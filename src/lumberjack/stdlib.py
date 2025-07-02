import logging

from lumberjack.functional import log
from lumberjack.logs import MessageType


class LumberjackHandler(logging.Handler):
    def emit(self, record):
        try:
            # TODO: improve conversion by adding relevant metadata to the log
            # entry
            log(
                f"[{record.levelname}] {record.name}: {record.msg}",
                MessageType.USER if record.levelno < 30 else MessageType.ERROR,
            )
        except Exception:
            self.handleError(record)


def hook_logging():
    root_logger = logging.getLogger()
    handler = LumberjackHandler()
    handler.setLevel(logging.NOTSET)
    root_logger.addHandler(handler)
