import logging

from bramble.functional import log
from bramble.logs import MessageType


class BrambleHandler(logging.Handler):
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
    handler = BrambleHandler()
    handler.setLevel(logging.NOTSET)
    root_logger.addHandler(handler)
