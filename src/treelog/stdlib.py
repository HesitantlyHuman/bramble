import logging

from treelog.functional import log
from treelog.logs import MessageType


class TreeLogHandler(logging.Handler):
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
    handler = TreeLogHandler()
    handler.setLevel(logging.NOTSET)
    root_logger.addHandler(handler)
