import logging

from bramble.functional import log
from bramble.logs import MessageType


class BrambleHandler(logging.Handler):
    def emit(self, record):
        try:
            metadata = {
                "logger": record.name,
                "level": record.levelname,
                "filename": record.filename,
                "lineno": record.lineno,
                "funcName": record.funcName,
                "module": record.module,
                "threadName": record.threadName,
                "processName": record.processName,
                "created": record.created,
            }

            # Convert values to only allowed types: str, int, float, bool
            for key, value in list(metadata.items()):
                if not isinstance(value, (str, int, float, bool)):
                    metadata[key] = str(value)

            log(
                f"[{record.levelname}] {record.name}: {record.getMessage()}",
                MessageType.USER if record.levelno < 30 else MessageType.ERROR,
                metadata,
            )
        except Exception:
            self.handleError(record)


def hook_logging():
    root_logger = logging.getLogger()
    handler = BrambleHandler()
    handler.setLevel(logging.NOTSET)
    root_logger.addHandler(handler)
