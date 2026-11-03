"""Background jobs (Celery over Valkey, TECH_STACK.md). Jobs are owned by a user (``job_runs``).

* A job is claimed with a compare-and-set (``queued``/``retrying`` -> ``running``), so a duplicate
  delivery of the same task does nothing.
* Only a transient database failure is retried (bounded, with backoff); every other failure ends
  the job as ``failed`` with a short error code and no payload.
* Job rows and results are readable only by their owner (see the API); a task receives only ids.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from celery import Celery
from sqlalchemy import update
from sqlalchemy.exc import OperationalError

from pandit_server.config import Settings
from pandit_server.container import Container, build_container
from pandit_server.db.models import JobRun

_log = logging.getLogger("pandit_server.jobs")

celery_app = Celery("pandit_server")
_container: Container | None = None

MAX_RETRIES = 3


class TransientJobError(Exception):
    """A failure worth retrying (for example the database was briefly unavailable)."""


def configure_celery(settings: Settings) -> None:
    celery_app.conf.update(
        broker_url=settings.valkey_url,
        result_backend=settings.valkey_url,
        task_always_eager=settings.celery_eager,
        task_eager_propagates=False,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        task_serializer="json",
        accept_content=["json"],
        result_expires=3600,
    )


def set_container(container: Container) -> None:
    global _container
    _container = container
    configure_celery(container.settings)


def get_container() -> Container:
    global _container
    if _container is None:  # a worker process builds its own
        _container = build_container(Settings())
        configure_celery(_container.settings)
    return _container


def claim_job(container: Container, job_id: uuid.UUID) -> bool:
    """Atomically move a job to ``running``; ``False`` if it is not claimable (already taken)."""
    with container.db.session() as session:
        result = session.execute(
            update(JobRun)
            .where(JobRun.id == job_id, JobRun.status.in_(("queued", "retrying")))
            .values(status="running", attempts=JobRun.attempts + 1)
        )
        return bool(result.rowcount == 1)  # type: ignore[attr-defined]


def finish_job(
    container: Container,
    job_id: uuid.UUID,
    *,
    status: str,
    result_ref: str | None = None,
    error_code: str | None = None,
) -> None:
    with container.db.session() as session:
        session.execute(
            update(JobRun)
            .where(JobRun.id == job_id)
            .values(status=status, result_ref=result_ref, error_code=error_code)
        )


def execute_report_job(container: Container, job_id: uuid.UUID, report_id: uuid.UUID) -> str:
    """Generate the report content. Returns the final job status."""
    from pandit_server.compose.reports import generate_report

    if not claim_job(container, job_id):
        return "skipped"
    try:
        generate_report(container, report_id)
    except OperationalError as exc:
        finish_job(container, job_id, status="retrying", error_code="database_unavailable")
        raise TransientJobError("database_unavailable") from exc
    except Exception as exc:  # noqa: BLE001
        _log.error("report_job_failed", extra={"error_type": type(exc).__name__})
        finish_job(container, job_id, status="failed", error_code=type(exc).__name__[:48])
        container.metrics.inc("jobs_total", kind="report", status="failed")
        return "failed"
    finish_job(container, job_id, status="succeeded", result_ref=str(report_id))
    container.metrics.inc("jobs_total", kind="report", status="succeeded")
    return "succeeded"


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="pandit.report",
    autoretry_for=(TransientJobError,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=MAX_RETRIES,
)
def report_task(self: Any, job_id: str, report_id: str) -> str:
    return execute_report_job(get_container(), uuid.UUID(job_id), uuid.UUID(report_id))


def enqueue_report(job_id: uuid.UUID, report_id: uuid.UUID) -> None:
    report_task.delay(str(job_id), str(report_id))
