from treelog.backends.filebased import FileReader, FileWriter

try:
    from treelog.backends.redis import RedisReader, RedisWriter
except ImportError:

    def _error_fn(*args, **kwargs):
        raise ImportError(
            "To use the redis tree logging backend, please install the redis extras. (e.g. `pip install treelog[redis]`)"
        )

    RedisReader = _error_fn
    RedisWriter = _error_fn
