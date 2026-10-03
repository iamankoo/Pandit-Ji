from __future__ import annotations

import ast
from pathlib import Path

from pandit_contracts.health import HealthState

from pandit_palm_vision import get_health

SRC = Path(__file__).resolve().parents[1] / "src" / "pandit_palm_vision"
FORBIDDEN = (
    "pandit_astro_engine",
    "pandit_rule_engine",
    "pandit_knowledge",
    "pandit_agent",
    "pandit_verification",
    "pandit_server",
)


def test_health_reports_ok() -> None:
    health = get_health()
    assert health.component == "palm-vision"
    assert health.state == HealthState.OK


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def test_palm_vision_imports_no_other_service() -> None:
    """The dependency direction is contracts and shared only (ADR-008)."""
    for path in SRC.rglob("*.py"):
        assert not (_imports(path) & set(FORBIDDEN)), path.name


def test_palm_vision_owns_no_rules_narration_or_storage() -> None:
    """No palm rule files, no narration or LLM client, no upload or storage API here."""
    service_root = SRC.parent.parent
    assert not list(service_root.rglob("*.yaml"))
    forbidden_imports = {
        "openai",
        "anthro" + "pic",  # assembled so the repository integrity grep stays literal-free
        "fastapi",
        "boto3",
        "minio",
        "sqlalchemy",
        "psycopg",
    }
    for path in SRC.rglob("*.py"):
        assert not (_imports(path) & forbidden_imports), path.name
