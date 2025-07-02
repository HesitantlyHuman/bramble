from typing import Dict, List, Self

from redis import asyncio as aioredis
import msgpack

from treelog.backend import TreeLogReader, TreeLogWriter
from treelog.logs import LogEntry

REDIS_PREFIX = "treelog:logging:"


class RedisWriter(TreeLogWriter):
    def __init__(self, redis_connection: aioredis.Redis):
        self.redis_connection = redis_connection

    async def async_append_entries(self, entries: Dict[str, List[LogEntry]]):
        pipe = self.redis_connection.pipeline()

        def _update_pipe(id: str, logs: List[LogEntry]):
            packed_logs: List[bytes] = [
                msgpack.packb(
                    (
                        log.timestamp,
                        log.message,
                        log.message_type.value,
                        log.entry_metadata,
                    )
                )
                for log in logs
            ]
            pipe.rpush(REDIS_PREFIX + id + ":logs", *packed_logs)

        for id, logs in entries.items():
            _update_pipe(id, logs)

        await pipe.execute()

    async def async_add_tags(self, tags: Dict[str, List[str]]):
        pipe = self.redis_connection.pipeline()

        for id, branch_tags in tags.items():
            pipe.sadd(REDIS_PREFIX + id + ":tags", *branch_tags)

        await pipe.execute()

    async def async_update_tree(self, relationships):
        pipe = self.redis_connection.pipeline()

        def _update_pipe(id: str, parent: str, children: List[str]):
            if parent:
                pipe.set(REDIS_PREFIX + id + ":parent", parent)

            if len(children) > 0:
                pipe.sadd(REDIS_PREFIX + id + ":children", *children)

        for id, (parent, children) in relationships.items():
            _update_pipe(id, parent, children)

        await pipe.execute()

    async def async_update_branch_metadata(self, metadata):
        pipe = self.redis_connection.pipeline()

        def _update_pipe(id: str, metadata: Dict[str, str | int | float | bool]):
            pipe.set(REDIS_PREFIX + id + ":metadata", msgpack.packb(metadata))

        for id, meta in metadata.items():
            _update_pipe(id, meta)

        await pipe.execute()

    @classmethod
    def from_socket(cls, host: str, port: str) -> Self:
        redis_url = f"redis://{host}:{port}"
        pool = aioredis.BlockingConnectionPool().from_url(redis_url, max_connections=10)
        redis_connection = aioredis.Redis(connection_pool=pool)
        return cls(redis_connection)


class RedisReader(TreeLogReader):
    def __init__(self):
        raise NotImplementedError()

    @classmethod
    def from_socket(cls, host: str, port: str) -> Self:
        raise NotImplementedError()
