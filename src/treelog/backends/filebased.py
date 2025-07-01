from typing import Dict, List, Any, Tuple

import aiofiles
import asyncio
import json
import os

from treelog.backend import TreeLogWriter, TreeLogReader
from treelog.logs import LogEntry, BranchData


class FileWriter(TreeLogWriter):
    _partition: Dict[str, int]
    _data: Dict[int, Dict[str, Any]]
    _open_partitions: List[int]
    _file_format: str = "treelog_logging_storage_partition_{}.jsonl"

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

    # TODO: wait until the end of these operations to update the appropriate partitions
    async def async_append_entries(
        self,
        entries: Dict[str, List[LogEntry]],
    ) -> None:
        async def _write_logs(id: str, logs: List[LogEntry]):
            partition = self._select_partition(id)
            logs = [
                {
                    "message": entry.message,
                    "timestamp": entry.timestamp,
                    "message_type": entry.message_type.value,
                    "entry_metadata": entry.entry_metadata,
                }
                for entry in logs
            ]

            self._data[partition][id]["messages"].extend(logs)
            await self._update_partition(partition)

        tasks = []
        for id, logs in entries.items():
            tasks.append(_write_logs(id, logs))

        await asyncio.gather(*tasks)

    async def async_add_tags(self, tags: Dict[str, List[str]]) -> None:
        async def _write_tags(id: str, tags: List[str]):
            partition = self._select_partition(id)
            self._data[partition][id]["tags"].extend(tags)
            await self._update_partition(partition)

        tasks = []
        for id, branch_tags in tags.items():
            tasks.append(_write_tags(id, branch_tags))

        await asyncio.gather(*tasks)

    async def async_update_tree(
        self, relationships: Dict[str, Tuple[str | None, List[str]]]
    ) -> None:
        async def _write_tree(id: str, parent: str | None, children: List[str]):
            partition = self._select_partition(id)
            self._data[partition][id]["metadata"].update(
                {"parent": parent, "children": children}
            )
            await self._update_partition(partition)

        tasks = []
        for id, (parent, children) in relationships.items():
            tasks.append(_write_tree(id, parent, children))

        await asyncio.gather(*tasks)

    async def async_update_branch_metadata(
        self, metadata: Dict[str, Dict[str, str | int | float | bool]]
    ) -> None:
        async def _write_meta(id: str, meta: Dict[str, Any]):
            partition = self._select_partition(id)
            self._data[partition][id]["metadata"].update(meta)
            await self._update_partition(partition)

        tasks = []
        for id, meta in metadata.items():
            tasks.append(_write_meta(id, meta))

        await asyncio.gather(*tasks)

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
        # TODO: we should be able to do this async, but for some reason that breaks things
        file_path = os.path.join(self.base_path, self._file_format.format(partition))
        data_to_write = self._data[partition]
        data_to_write = json.dumps(data_to_write)
        with open(file_path, "w") as f:
            f.write(data_to_write)


class FileReader(TreeLogReader):
    _data: Dict[str, BranchData]
    _with_tags: Dict[str, List[str]]

    def __init__(self, base_path: str):
        self.base_path = base_path
        self.load_data()

    def load_data(self):
        self._data = {}
        self._with_tags = {}
        for file_name in os.listdir(self.base_path):
            file_path = os.path.join(self.base_path, file_name)
            try:
                data = self.load_partition(file_path)
                for logger_id, flow_log in data.items():
                    self._data[logger_id] = flow_log
                    for tag in flow_log.tags:
                        if tag not in self._with_tags:
                            self._with_tags[tag] = []
                        self._with_tags[tag].append(logger_id)
            except Exception as e:
                pass

    def load_partition(self, partition_path: str) -> Dict[str, BranchData]:
        with open(partition_path, "r") as f:
            data = f.read()
            data = json.loads(data)

        # Now convert the data to TreeLog objects
        flow_logs = {}
        for logger_id, flow_data in data.items():
            messages = [LogEntry(**entry) for entry in flow_data["messages"]]
            metadata = {
                key: value
                for key, value in flow_data["metadata"].items()
                if key not in ["parent", "children", "name"]
            }
            flow_logs[logger_id] = BranchData(
                id=logger_id,
                name=flow_data["metadata"]["name"],
                parent=flow_data["metadata"]["parent"],
                children=flow_data["metadata"]["children"],
                messages=messages,
                metadata=metadata,
                tags=flow_data["tags"],
            )

        return flow_logs

    def get_branches(self, branch_ids: List[str]) -> Dict[str, BranchData]:
        data = {}
        for branch_id in branch_ids:
            data[branch_id] = self._data[branch_id]
        return data

    def get_branch_ids(self) -> List[str]:
        return list(self._data.keys())


if __name__ == "__main__":
    path = "test"
    reader = FileReader(path)

    async def main():
        flow_log_ids = await reader.async_get_branch_ids()
        data = await reader.async_get_branches(flow_log_ids)
        print(data)

    asyncio.run(main())
