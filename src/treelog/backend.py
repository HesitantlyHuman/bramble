from typing import Any, Dict, List

import aiofiles
import json
import os

from treelog.logs import LogEntry, TreeLog

# TODO: maybe merge these?

# TODO: update docstrings


# TODO: Document the fact that you only need to implement either the sync or
# async version of any of the backend methods.
class TreeLoggingWriter:
    # TODO: do we want to provide entries for multiple branches?
    def append_entry(
        self,
        branch_id: str,
        log_entry: LogEntry | List[LogEntry],
    ) -> None:
        """Append a log entry to the tree logger for a specific node.

        Args:
            node_id (Union[str, List[str]]): The ID of the tree logger.
            log_entry (LogEntry): The log entry to append.
        """
        raise NotImplementedError()

    async def async_append_entry(
        self,
        branch_id: str,
        log_entry: LogEntry | List[LogEntry],
    ) -> None:
        """Append a log entry to the tree logger for a specific node.

        Args:
            node_id (Union[str, List[str]]): The ID of the tree logger.
            log_entry (LogEntry): The log entry to append.
        """
        self.append_entry(branch_id=branch_id, log_entry=log_entry)

    def add_tags(self, branch_id: str, tags: str | List[str]) -> None:
        """Add tags to the tree logger.

        Does not remove existing tags. Does not add duplicate tags.

        Args:
            logger_id (str): The ID of the tree logger.
            tags (Union[str, List[str]]): The tags to add. Can be a single tag or a list.
        """
        raise NotImplementedError()

    async def async_add_tags(self, branch_id: str, tags: str | List[str]) -> None:
        """Add tags to the tree logger.

        Does not remove existing tags. Does not add duplicate tags.

        Args:
            logger_id (str): The ID of the tree logger.
            tags (Union[str, List[str]]): The tags to add. Can be a single tag or a list.
        """
        self.add_tags(branch_id=branch_id, tags=tags)

    def remove_tags(self, branch_id: str, tags: str | List[str]) -> None:
        """Removes tags from the tree logger.

        If a tag does not exist, it is ignored.

        Args:
            logger_id (str): The ID of the tree logger.
            tags (Union[str, List[str]]): The tags to remove. Can be a single tag or a list.
        """
        raise NotImplementedError()

    async def async_remove_tags(self, branch_id: str, tags: str | List[str]) -> None:
        """Removes tags from the tree logger.

        If a tag does not exist, it is ignored.

        Args:
            logger_id (str): The ID of the tree logger.
            tags (Union[str, List[str]]): The tags to remove. Can be a single tag or a list.
        """
        self.remove_tags(branch_id=branch_id, tags=tags)

    # TODO: add docstrings
    def update_tree(self, branch_id: str, parent: str, children: List[str]) -> None:
        raise NotImplementedError()

    async def async_update_tree(
        self, branch_id: str, parent: str, children: List[str]
    ) -> None:
        self.update_tree(branch_id=branch_id, parent=parent, children=children)

    def update_branch_metadata(
        self, branch_id: str, metadata: Dict[str, str | int | float | bool]
    ) -> None:
        """Updates the metadata of a tree logger with an arbitrary dictionary.

        Creates metadata if it does not exist. If the new metadata is a subset of the
        existing metadata, only the keys provided in the new metadata will be updated.

        Args:
            logger_id (str): The ID of the tree logger.
            metadata (Dict[str, Any]): The metadata to update.
        """
        raise NotImplementedError()

    async def async_update_branch_metadata(
        self, branch_id: str, metadata: Dict[str, Any]
    ) -> None:
        """Updates the metadata of a tree logger with an arbitrary dictionary.

        Creates metadata if it does not exist. If the new metadata is a subset of the
        existing metadata, only the keys provided in the new metadata will be updated.

        Args:
            logger_id (str): The ID of the tree logger.
            metadata (Dict[str, Any]): The metadata to update.
        """
        self.update_logger_metadata(branch_id=branch_id, metadata=metadata)


class TreeLoggingReader:
    def get_logs(self, logger_id: str | List[str]) -> TreeLog | List[TreeLog]:
        """Get the log for a tree logger.

        Args:
            logger_id (Union[str, List[str]]): The ID or IDs of the tree loggers.

        Returns:
            Union[TreeLog, List[TreeLog]]: The log for the tree logger or tree loggers.
        """
        raise NotImplementedError()

    async def async_get_logs(
        self, logger_id: str | List[str]
    ) -> TreeLog | List[TreeLog]:
        """Get the log for a tree logger.

        Args:
            logger_id (Union[str, List[str]]): The ID or IDs of the tree loggers.

        Returns:
            Union[TreeLog, List[TreeLog]]: The log for the tree logger or tree loggers.
        """
        return self.get_logs(logger_id=logger_id)

    def get_logger_ids_by_tag(self, tag: str) -> List[str]:
        """Get the IDs of tree loggers with a specific tag.

        Args:
            tag (str): The tag to search for.

        Returns:
            List[str]: The IDs of tree loggers with the tag.
        """
        raise NotImplementedError()

    async def async_get_logger_ids_by_tag(self, tag: str) -> List[str]:
        """Get the IDs of tree loggers with a specific tag.

        Args:
            tag (str): The tag to search for.

        Returns:
            List[str]: The IDs of tree loggers with the tag.
        """
        return self.get_logger_ids_by_tag(tag=tag)

    def get_logger_ids(self) -> List[str]:
        """Get the IDs of all tree loggers.

        Returns:
            List[str]: The IDs of all tree loggers.
        """
        raise NotImplementedError()

    async def async_get_logger_ids(self) -> List[str]:
        """Get the IDs of all tree loggers.

        Returns:
            List[str]: The IDs of all tree loggers.
        """
        return self.get_logger_ids()

    def get_logger_metadata(self, id: str) -> Dict[str, Any]:
        """Gets metadata for a specific logger.

        Args:
            id (`str`): The ID for the requested logger.

        Returns:
            Dict[str, Any]: The metada for the logger.
        """
        raise NotImplementedError()

    async def async_get_logger_metadata(self, id: str) -> Dict[str, Any]:
        """Gets metadata for a specific logger.

        Args:
            id (`str`): The ID for the requested logger.

        Returns:
            Dict[str, Any]: The metada for the logger.
        """
        return self.get_logger_metadata()


# TODO: fix that this overwrites existing files
class FileTreeLoggingWriter(TreeLoggingWriter):
    _partition: Dict[str, int]
    _data: Dict[int, Dict[str, Any]]
    _open_partitions: List[int]
    _file_format: str = "powergrader_ai_logging_storage_partition_{}.jsonl"

    def __init__(
        self,
        base_path: str,
        num_flows_per_partition: int = 1000,
        num_concurrent_writes: int = 16,
    ):
        self.base_path = base_path
        self.num_flows_per_partition = num_flows_per_partition
        self._open_partitions = list(range(num_concurrent_writes))
        self._next_partition = num_concurrent_writes
        self._partition = {}
        self._data = {}
        for partition in self._open_partitions:
            self._create_partition(partition)
        os.makedirs(base_path, exist_ok=True)

    async def async_append_entry(
        self, logger_id: str, log_entry: LogEntry | List[LogEntry]
    ) -> None:
        partition = self._select_partition(logger_id)
        if not isinstance(log_entry, list):
            log_entry = [log_entry]
        log_entry = [
            {
                "message": entry.message,
                "timestamp": entry.timestamp,
                "message_type": entry.message_type.value,
                "entry_metadata": entry.entry_metadata,
            }
            for entry in log_entry
        ]

        self._data[partition][logger_id]["messages"].extend(log_entry)
        await self._update_partition(partition)

    async def async_add_tags(self, logger_id: str, tags: str | List[str]) -> None:
        partition = self._select_partition(logger_id)
        if not isinstance(tags, list):
            tags = [tags]
        self._data[partition][logger_id]["tags"].extend(tags)
        await self._update_partition(partition)

    async def async_remove_tags(self, logger_id: str, tags: str | List[str]) -> None:
        partition = self._select_partition(logger_id)
        if not isinstance(tags, list):
            tags = [tags]
        self._data[partition][logger_id]["tags"] = [
            tag for tag in self._data[partition][logger_id]["tags"] if tag not in tags
        ]
        await self._update_partition(partition)

    async def async_update_flow_metadata(
        self, logger_id: str, metadata: Dict[str, Any]
    ) -> None:
        partition = self._select_partition(logger_id)
        self._data[partition][logger_id]["metadata"].update(metadata)
        await self._update_partition(partition)

    def _select_partition(self, logger_id: str) -> int:
        if logger_id in self._partition:
            return self._partition[logger_id]
        id_bytes = logger_id.encode("utf-8")
        open_partition_index = int.from_bytes(id_bytes, "big") % len(
            self._open_partitions
        )
        partition = self._open_partitions[open_partition_index]
        if partition not in self._data:
            self._create_partition(partition)
        if logger_id not in self._data[partition]:
            self._data[partition][logger_id] = {
                "messages": [],
                "metadata": {},
                "tags": [],
            }
        self._partition[logger_id] = partition

        if len(self._data[partition]) >= self.num_flows_per_partition:
            self._open_partitions.remove(partition)
            self._open_partitions.append(self._next_partition)
            self._next_partition += 1

        return partition

    def _create_partition(self, partition: int):
        self._data[partition] = {}

    async def _update_partition(self, partition: int):
        file_path = os.path.join(self.base_path, self._file_format.format(partition))
        data_to_write = self._data[partition]
        data_to_write = json.dumps(data_to_write)
        async with aiofiles.open(file_path, "w") as f:
            await f.write(data_to_write)


class FileTreeLoggingReader(TreeLoggingReader):
    _data: Dict[str, TreeLog]
    _with_tags: Dict[str, List[str]]

    def __init__(self, base_path: str):
        self.base_path = base_path
        self._has_data = False

    async def load_data(self):
        self._data = {}
        self._with_tags = {}
        for file_name in os.listdir(self.base_path):
            file_path = os.path.join(self.base_path, file_name)
            try:
                data = await self.load_partition(file_path)
                for logger_id, flow_log in data.items():
                    self._data[logger_id] = flow_log
                    for tag in flow_log.tags:
                        if tag not in self._with_tags:
                            self._with_tags[tag] = []
                        self._with_tags[tag].append(logger_id)
            except Exception:
                pass

    async def load_partition(self, partition_path: str) -> Dict[str, TreeLog]:
        async with aiofiles.open(partition_path, "r") as f:
            data = await f.read()
            data = json.loads(data)

        # Now convert the data to TreeLog objects
        flow_logs = {}
        for logger_id, flow_data in data.items():
            messages = [
                LogEntry(
                    message=entry["message"],
                    timestamp=entry["timestamp"],
                    message_type=entry["message_type"],
                    entry_metadata=entry["entry_metadata"],
                )
                for entry in flow_data["messages"]
            ]
            flow_logs[logger_id] = TreeLog(
                messages=messages,
                metadata=flow_data["metadata"],
                tags=flow_data["tags"],
            )

        return flow_logs

    async def async_get_flow_logs(
        self, logger_id: str | List[str]
    ) -> TreeLog | List[TreeLog]:
        if not self._has_data:
            await self.load_data()
            self._has_data = True
        if isinstance(logger_id, list):
            return [self._data[id] for id in logger_id]
        return self._data[logger_id]

    async def async_get_flow_log_ids_by_tag(self, tag: str) -> List[str]:
        if not self._has_data:
            await self.load_data()
            self._has_data = True
        return self._with_tags.get(tag, [])

    async def async_get_flow_log_ids(self) -> List[str]:
        if not self._has_data:
            await self.load_data()
            self._has_data = True
        return list(self._data.keys())


# class FileLoggingStorage(LoggingStorage):
#     data: Dict[str, Any]

#     def __init__(self, base_path: str, num_partitions: int = 16):
#         self.base_path = base_path
#         self.file_path_format = os.path.join(base_path, FILE_NAME)
#         os.makedirs(base_path, exist_ok=True)
#         self.num_partitions = num_partitions
#         self.data = {}
#         self.load()
#         self.save()

#     def load(self):
#         for i in range(self.num_partitions):
#             self.data[i] = {}

#         if os.path.exists(self.base_path):
#             for i in range(self.num_partitions):
#                 file_path = self.file_path_format.format(i)
#                 if os.path.exists(file_path):
#                     with open(file_path, "r") as f:
#                         for line in f.readlines():
#                             data = json.loads(line)
#                             partition = self.hash_id(data["id"])
#                             self.data[partition][data["id"]] = data

#     def save(self):
#         for i in range(self.num_partitions):
#             self.write_partition(i)

#     async def append_message(self, log_id: str, message: str, timestamp: float = None):
#         partition = self.hash_id(log_id)
#         if log_id not in self.data[partition]:
#             self.data[partition][log_id] = {"messages": [], "metadata": {}}
#         self.data[partition][log_id]["messages"].append(
#             {"content": message, "timestamp": timestamp}
#         )
#         await self.async_write_partition(partition)

#     async def update_metadata(self, log_id: str, metadata: Dict[str, Any]):
#         partition = self.hash_id(log_id)
#         if log_id not in self.data[partition]:
#             self.data[partition][log_id] = {"messages": [], "metadata": {}}
#         self.data[partition][log_id]["metadata"].update(metadata)
#         await self.async_write_partition(partition)

#     async def get_messages(self, log_id: str) -> List[Dict[str, Any]]:
#         partition = self.hash_id(log_id)
#         return self.data[partition][log_id]["messages"]

#     async def get_metadata(self, log_id: str) -> Dict[str, Any]:
#         partition = self.hash_id(log_id)
#         return self.data[partition][log_id]["metadata"]

#     async def get_flow_log(self, log_id: str) -> Dict[str, Any]:
#         partition = self.hash_id(log_id)
#         return self.data[partition][log_id]

#     def hash_id(self, id: str) -> int:
#         id_bytes = id.encode("utf-8")
#         return int.from_bytes(id_bytes, "big") % self.num_partitions

#     def stringify_partition(self, partition: int) -> str:
#         string = ""
#         for id, data in self.data[partition].items():
#             data_with_id = data.copy()
#             data_with_id["id"] = id
#             string += json.dumps(data_with_id) + "\n"
#         return string

#     async def async_write_partition(self, partition: int):
#         file_path = self.file_path_format.format(partition)
#         str_data = self.stringify_partition(partition)
#         async with aiofiles.open(file_path, "w") as f:
#             await f.write(str_data)

#     def write_partition(self, partition: int):
#         file_path = self.file_path_format.format(partition)
#         str_data = self.stringify_partition(partition)
#         with open(file_path, "w") as f:
#             f.write(str_data)

#     async def write_to_redis(self, redis_connection: aioredis.Redis):
#         redis_storage = RedisLoggingStorage(redis_connection)
#         transfer_jobs = []
#         for partition in range(self.num_partitions):
#             for log_id in self.data[partition].keys():
#                 transfer_jobs.append(
#                     transfer_file_log_to_redis(log_id, self, redis_storage)
#                 )
#         await asyncio.gather(*transfer_jobs)


# REDIS_PREFIX = "powergrader_ai:logging:"


# class RedisLoggingStorage(LoggingStorage):
#     def __init__(self, redis_connection: aioredis.Redis):
#         self.redis_connection = redis_connection

#     async def append_message(self, log_id: str, message: str, timestamp: float = None):
#         stringified_message = json.dumps(
#             {
#                 "content": message,
#                 "timestamp": timestamp,
#             }
#         )
#         await self.redis_connection.rpush(REDIS_PREFIX + log_id, stringified_message)

#     async def update_metadata(self, log_id: str, metadata: Dict[str, Any]):
#         stringified_metadata = json.dumps(metadata)
#         await self.redis_connection.set(
#             REDIS_PREFIX + log_id + "_metadata", stringified_metadata
#         )

#     async def get_messages(self, log_id: str) -> List[Dict[str, Any]]:
#         stringified_messages = await self.redis_connection.lrange(
#             REDIS_PREFIX + log_id, 0, -1
#         )
#         return [json.loads(message) for message in stringified_messages]

#     async def get_metadata(self, log_id: str) -> Dict[str, Any]:
#         stringified_metadata = await self.redis_connection.get(
#             REDIS_PREFIX + log_id + "_metadata"
#         )
#         return json.loads(stringified_metadata)

#     async def get_flow_log(self, log_id: str) -> Dict[str, Any]:
#         return {
#             "messages": await self.get_messages(log_id),
#             "metadata": await self.get_metadata(log_id),
#         }

#     @classmethod
#     def from_connection_info(cls, host: str, port: str) -> "RedisLoggingStorage":
#         redis_url = f"redis://{host}:{port}"
#         pool = aioredis.BlockingConnectionPool().from_url(
#             redis_url, max_connections=100
#         )
#         redis_connection = aioredis.Redis(connection_pool=pool)
#         return cls(redis_connection)

#     async def write_to_file(self, file_path: str):
#         file_storage = FileLoggingStorage(file_path)
#         transfer_jobs = []
#         for log_id in self.redis_connection.keys(REDIS_PREFIX + "*"):
#             transfer_jobs.append(transfer_redis_log_to_file(log_id, self, file_storage))
#         await asyncio.gather(*transfer_jobs)


# async def transfer_redis_log_to_file(
#     log_id: str, redis_storage: RedisLoggingStorage, file_storage: FileLoggingStorage
# ):
#     flow_log = await redis_storage.get_flow_log(log_id)
#     await file_storage.update_metadata(log_id, flow_log["metadata"])
#     for message in flow_log["messages"]:
#         await file_storage.append_message(
#             log_id, message["content"], message["timestamp"]
#         )


# async def transfer_file_log_to_redis(
#     log_id: str, file_storage: FileLoggingStorage, redis_storage: RedisLoggingStorage
# ):
#     flow_log = await file_storage.get_flow_log(log_id)
#     await redis_storage.update_metadata(log_id, flow_log["metadata"])
#     for message in flow_log["messages"]:
#         await redis_storage.append_message(
#             log_id, message["content"], message["timestamp"]
#         )
