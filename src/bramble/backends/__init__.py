from bramble.backends.file_backend import FileReader, FileWriter

try:
    from bramble.backends.redis_backend import RedisReader, RedisWriter
except ImportError:

    class _RedisError:
        def __call__(self, *args, **kwargs):
            raise ImportError(
                "To use the redis bramble backend, please install the redis extras. (e.g. `pip install bramble[redis]`)"
            )

        def __getattribute__(self, name):
            raise ImportError(
                "To use the redis bramble backend, please install the redis extras. (e.g. `pip install bramble[redis]`)"
            )

    REDIS_ERROR = _RedisError()

    RedisReader = REDIS_ERROR
    RedisWriter = REDIS_ERROR
