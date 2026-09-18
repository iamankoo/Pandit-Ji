import json
import logging

from pandit_shared.logging import bind_request_id, configure_logging


def test_configure_logging_emits_json(capsys) -> None:
    configure_logging(service="astro-engine", environment="test", level="INFO")
    bind_request_id("req-123")
    logging.getLogger("pandit.test").info("hello")

    captured = capsys.readouterr()
    line = captured.out.strip().splitlines()[-1]
    record = json.loads(line)

    assert record["service"] == "astro-engine"
    assert record["environment"] == "test"
    assert record["level"] == "INFO"
    assert record["message"] == "hello"
    assert record["request_id"] == "req-123"

    bind_request_id(None)
