from typing import Dict, List, Self

from redis import asyncio as aioredis
import msgpack

from bramble.backends.base import BrambleWriter, BrambleReader
from bramble.logs import LogEntry, BranchData, MessageType

REDIS_PREFIX = "bramble:logging:"


class RedisWriter(BrambleWriter):
    redis_connection: aioredis.Redis

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


class RedisReader(BrambleReader):
    redis_connection: aioredis.Redis

    def __init__(self, redis_connection: aioredis.Redis):
        self.redis_connection = redis_connection

    async def async_get_branches(self, branch_ids: List[str]) -> Dict[str, BranchData]:
        """Gets the data for tree logger branches.

        Args:
            branch_ids (List[str]): The IDs of the tree logger branches.

        Returns:
            Dict[str, BranchData]: A dict of branch IDs to the corresponding
                BranchData object.
        """
        pipe = self.redis_connection.pipeline()

        for branch_id in branch_ids:
            pipe.lrange(REDIS_PREFIX + branch_id + ":logs", 0, -1)
            pipe.smembers(REDIS_PREFIX + branch_id + ":tags")
            pipe.get(REDIS_PREFIX + branch_id + ":metadata")
            pipe.get(REDIS_PREFIX + branch_id + ":parent")
            pipe.smembers(REDIS_PREFIX + branch_id + ":children")

        output = await pipe.execute()
        branches = [
            [branch_id] + output[i : i + 5]
            for branch_id, i in zip(branch_ids, range(0, len(output), 5))
        ]
        formatted = []
        for id, logs, tags, metadata, parent, children in branches:
            metadata = msgpack.loads(metadata)
            if parent is not None:
                parent = parent.decode()
            children = {child.decode() for child in children}
            logs = [msgpack.loads(log) for log in logs]
            tags = list({tag.decode() for tag in tags})
            logs = [
                LogEntry(
                    message=message,
                    timestamp=timestamp,
                    message_type=MessageType(message_type),
                    entry_metadata=entry_metadata,
                )
                for timestamp, message, message_type, entry_metadata in logs
            ]
            formatted.append(
                BranchData(
                    id=id,
                    name=metadata["name"],
                    parent=parent,
                    children=children,
                    messages=logs,
                    tags=tags,
                    metadata=metadata,
                )
            )
        return {data.id: data for data in formatted}

    async def async_get_branch_ids(self) -> List[str]:
        """Gets the IDs of all tree logger branches.

        Returns:
            List[str]: The IDs of all tree logger branches.
        """
        keys: List[bytes] = await self.redis_connection.keys(REDIS_PREFIX + "*:logs")
        keys = [key.decode().replace(REDIS_PREFIX, "").split(":")[0] for key in keys]
        return keys

    @classmethod
    def from_socket(cls, host: str, port: str) -> Self:
        redis_url = f"redis://{host}:{port}"
        pool = aioredis.BlockingConnectionPool().from_url(redis_url, max_connections=10)
        redis_connection = aioredis.Redis(connection_pool=pool)
        return cls(redis_connection)


if __name__ == "__main__":
    reader = RedisReader.from_socket("127.0.0.1", "6379")

    import asyncio

    async def main():
        keys = await reader.async_get_branch_ids()
        await reader.async_get_branches(keys)

    asyncio.run(main())
