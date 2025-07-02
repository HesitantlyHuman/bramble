from lumberjack.backends.filebased import FileReader, FileWriter

try:
    from lumberjack.backends.redis import RedisReader, RedisWriter
except ImportError:

    class _RedisError:
        def __call__(self, *args, **kwargs):
            raise ImportError(
                "To use the redis lumberjack backend, please install the redis extras. (e.g. `pip install lumberjack[redis]`)"
            )

        def __getattribute__(self, name):
            raise ImportError(
                "To use the redis lumberjack backend, please install the redis extras. (e.g. `pip install lumberjack[redis]`)"
            )

    REDIS_ERROR = _RedisError()

    RedisReader = REDIS_ERROR
    RedisWriter = REDIS_ERROR
