import logging
from unittest.mock import patch, MagicMock

import pytest

from bramble.stdlib import BrambleHandler, hook_logging
from bramble.logs import MessageType


def make_log_record(level, msg="test msg"):
    return logging.LogRecord(
        name="test_logger",
        level=level,
        pathname=__file__,
        lineno=123,
        msg=msg,
        args=(),
        exc_info=None,
    )


@patch("bramble.stdlib.log")
def test_emit_user_level_logs(log_mock):
    handler = BrambleHandler()
    record = make_log_record(logging.INFO, "info level message")
    handler.emit(record)

    log_mock.assert_called_once()
    msg, msg_type, metadata = log_mock.call_args[0]
    assert "[INFO] test_logger" in msg
    assert msg_type == MessageType.USER
    assert isinstance(metadata, dict)
    assert metadata["level"] == "INFO"
    assert metadata["logger"] == "test_logger"


@patch("bramble.stdlib.log")
def test_emit_error_level_logs(log_mock):
    handler = BrambleHandler()
    record = make_log_record(logging.ERROR, "uh oh")
    handler.emit(record)

    log_mock.assert_called_once()
    _, msg_type, _ = log_mock.call_args[0]
    assert msg_type == MessageType.ERROR


@patch("bramble.stdlib.log")
def test_emit_metadata_casting(log_mock):
    handler = BrambleHandler()
    record = make_log_record(logging.INFO)

    # Inject a non-serializable field into the record (e.g., an object)
    record.processName = object()

    handler.emit(record)

    _, _, metadata = log_mock.call_args[0]
    # Should be stringified
    assert isinstance(metadata["processName"], str)


def test_hook_logging_adds_handler():
    root_logger = logging.getLogger()
    original_handler_count = len(root_logger.handlers)

    hook_logging()

    assert any(isinstance(h, BrambleHandler) for h in root_logger.handlers)
    assert len(root_logger.handlers) >= original_handler_count + 1


@patch("bramble.stdlib.log", side_effect=Exception("fail"))
def test_emit_handles_exceptions_gracefully(log_mock):
    handler = BrambleHandler()
    record = make_log_record(logging.INFO)

    # Should not raise
    handler.emit(record)
