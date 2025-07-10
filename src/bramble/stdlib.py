import logging

from bramble.logs import MessageType


class BrambleHandler(logging.Handler):
    def __init__(self, level=0):
        # Cannot import at top of file because of circular imports
        from bramble.contextual import log

        super().__init__(level)
        self.log_fn = log

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

            self.log_fn(
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
