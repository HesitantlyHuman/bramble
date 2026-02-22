from typing import Dict, List, Tuple, Set, Any

import asyncio

from bramble.log_objects import LogEntry
from bramble.compression import EntryWriter, MetadataWriter
from bramble.backends.base import BrambleBackend

from utils import _generate_id


# TODO: Document functions, settings
# TODO: Add support for loading the active chunks
class BrambleWriter:
    bramble_backend: BrambleBackend
    num_simultaneous_chunks: int
    chunk_size: int
    compression_quality: int
    max_assignment_imbalance_factor: float
    base_assignment_imbalance_num: int

    def __init__(
        self,
        bramble_backend: BrambleBackend,
        num_simultaneous_chunks: int = 32,
        chunk_size: int = 2**24,
        compression_quality: int = 6,
        max_assignment_imbalance_factor: float = 3.0,
        base_assignment_imbalance_num: int = 10,
    ):
        self.bramble_backend = bramble_backend
        self.num_simultaneous_chunks = num_simultaneous_chunks
        self.chunk_size = chunk_size
        self.max_assignment_imbalance_factor = max_assignment_imbalance_factor
        self.base_assignment_imbalance_num = base_assignment_imbalance_num

        self._entry_compressors = {
            _generate_id("ec"): EntryWriter.new(quality=compression_quality)
            for _ in range(self.num_simultaneous_chunks)
        }
        self._meta_compressors = {
            _generate_id("mc"): MetadataWriter.new(quality=compression_quality)
            for _ in range(self.num_simultaneous_chunks)
        }

        self._id_to_entry_compressor_map: Dict[str, str] = {}
        self._id_to_meta_compressor_map: Dict[str, str] = {}

        self._name_to_entry_compressor_map: Dict[str, Set[str]] = {}
        self._name_to_meta_compressor_map: Dict[str, Set[str]] = {}

        self._entry_chunk_to_ids_and_names: Dict[int, Set[Tuple[str, str]]] = {}
        self._meta_chunk_to_ids_and_names: Dict[int, Set[Tuple[str, str]]] = {}

        self._entry_chunk_assignment_options: Set[str] = {}
        self._meta_chunk_assignment_options: Set[str] = {}

        self._chunk_sizes = Dict[str, int] = {}

    def _assign_entry_chunk(self, branch_id: str, name: str) -> str:
        current_num_entry_assignments = {
            chunk_id: len(vals)
            for chunk_id, vals in self._entry_chunk_to_ids_and_names.items()
        }
        max_entry_allowed = int(
            (
                min(list(current_num_entry_assignments.values()))
                + self.base_assignment_imbalance_num
            )
            * self.max_assignment_imbalance_factor
        )
        if len(self._entry_chunk_assignment_options) == 0:
            self._entry_chunk_assignment_options = set(self._entry_compressors.keys())

        # First, attempt to assign by name, then, just assign to any chunk
        for entry_compressor_candidates in [
            self._name_to_entry_compressor_map.get(name),
            self._entry_chunk_assignment_options,
        ]:
            if entry_compressor_candidates is not None:
                ids_and_sizes = [
                    (candidate, current_num_entry_assignments[candidate])
                    for candidate in entry_compressor_candidates
                ]
                ids_and_sizes.sort(key=lambda x: x[1])
                selected_id, current_num_assignments = ids_and_sizes[0]
                if current_num_assignments <= max_entry_allowed:
                    self._id_to_entry_compressor_map[branch_id] = selected_id
                    if name not in self._name_to_entry_compressor_map:
                        self._name_to_entry_compressor_map[name] = set()
                    self._name_to_entry_compressor_map[name].add(selected_id)
                    self._entry_chunk_to_ids_and_names[selected_id].add(
                        (branch_id, name)
                    )
                    self._entry_chunk_assignment_options.remove(selected_id)
                    return selected_id

        raise RuntimeError(f"Reached unexpected termination condition!")

    def _assign_meta_chunk(self, branch_id: str, name: str) -> str:
        current_num_meta_assignments = {
            chunk_id: len(vals)
            for chunk_id, vals in self._meta_chunk_to_ids_and_names.items()
        }
        max_meta_allowed = int(
            (
                min(list(current_num_meta_assignments.values()))
                + self.base_assignment_imbalance_num
            )
            * self.max_assignment_imbalance_factor
        )
        if len(self._meta_chunk_assignment_options) == 0:
            self._meta_chunk_assignment_options = set(self._meta_compressors.keys())

        # First, attempt to assign by name, then, just assign to any chunk
        for meta_compressor_candidates in [
            self._name_to_meta_compressor_map.get(name),
            self._meta_chunk_assignment_options,
        ]:
            if meta_compressor_candidates is not None:
                ids_and_sizes = [
                    (candidate, current_num_meta_assignments[candidate])
                    for candidate in meta_compressor_candidates
                ]
                ids_and_sizes.sort(key=lambda x: x[1])
                selected_id, current_num_assignments = ids_and_sizes[0]
                if current_num_assignments <= max_meta_allowed:
                    self._id_to_meta_compressor_map[branch_id] = selected_id
                    if name not in self._name_to_meta_compressor_map:
                        self._name_to_meta_compressor_map[name] = set()
                    self._name_to_meta_compressor_map[name].add(selected_id)
                    self._meta_chunk_to_ids_and_names[selected_id].add(
                        (branch_id, name)
                    )
                    self._meta_chunk_assignment_options.remove(selected_id)
                    return selected_id

        raise RuntimeError(f"Reached unexpected termination condition!")

    def _assign_chunk(self, branch_id: str, name: str) -> Tuple[str, str]:
        """Assigns branches to chunks."""
        return (
            self._assign_entry_chunk(branch_id=branch_id, name=name),
            self._assign_meta_chunk(branch_id=branch_id, name=name),
        )

    def _assign_chunks(
        self, ids_and_names: Set[Tuple[str, str]]
    ) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
        entry_assignments = {}
        meta_assignments = {}
        for id, name in ids_and_names:
            entry_assignment, meta_assignment = self._assign_chunk(
                branch_id=id, name=name
            )
            entry_assignments[id] = set([entry_assignment])
            meta_assignments[id] = set([meta_assignment])
        return entry_assignments, meta_assignments

    async def add_branches(self, ids_and_names: Set[Tuple[str, str]]) -> None:
        """Adds new branches to the backend storage."""
        entry_chunk_assignments, meta_chunk_assignments = self._assign_chunks(
            ids_and_names=ids_and_names
        )
        ids_to_add = set([item[0] for item in ids_and_names])
        master_list_task = self.bramble_backend.async_add_branches(ids_to_add)
        entry_assignment_task = self.bramble_backend.async_assign_chunks(
            branch_chunks=entry_chunk_assignments, chunk_type="ec"
        )
        meta_assignment_task = self.bramble_backend.async_assign_chunks(
            branch_chunks=meta_chunk_assignments, chunk_type="mc"
        )

        await asyncio.gather(
            master_list_task, entry_assignment_task, meta_assignment_task
        )

    def _close_branch(self, branch_id: str) -> None:
        """Mark branch as closed."""
        assigned_entry_chunk, assigned_meta_chunk = (
            self._id_to_entry_compressor_map[branch_id],
            self._id_to_meta_compressor_map[branch_id],
        )
        del self._id_to_entry_compressor_map[branch_id]
        del self._id_to_meta_compressor_map[branch_id]

        self._entry_chunk_to_ids_and_names[assigned_entry_chunk] = {
            item
            for item in self._entry_chunk_to_ids_and_names[assigned_entry_chunk]
            if item[0] == branch_id
        }
        self._meta_chunk_to_ids_and_names[assigned_meta_chunk] = {
            item
            for item in self._meta_chunk_to_ids_and_names[assigned_meta_chunk]
            if item[0] == branch_id
        }

    async def close_branches(self, branch_ids: List[str]) -> None:
        """Mark branches as closed."""
        for branch_id in branch_ids:
            self._close_branch(branch_id=branch_id)

    async def append_entries(
        self,
        entries: Dict[str, List[LogEntry]],
    ) -> None:
        """Appends log entries to the tree logger storage.

        Args:
            log_entries (Dict[str, List[LogEntry]]): The log entries to append,
            keyed by branch id.
        """
        # TODO: Change to new chunks if we have exceeded our size
        logging_data_by_chunk: Dict[str, bytes] = {}
        for branch_id, log_entries in entries.items():
            chunk_id = self._id_to_entry_compressor_map[branch_id]
            if chunk_id not in logging_data_by_chunk:
                logging_data_by_chunk[chunk_id] = b""
            for entry in log_entries:
                logging_data_by_chunk[chunk_id] += self._entry_compressors[
                    chunk_id
                ].add(branch_id=branch_id, entry=entry)

        await self.bramble_backend.async_append_data(chunk_data=logging_data_by_chunk)

    async def update_branch_info(
        self,
        parents: Dict[str, str] | None,
        children: Dict[str, Set[str]] | None,
        tags: Dict[str, Set[str]] | None,
        metadata: Dict[str, Dict[str, str | int | float | bool]] | None,
    ) -> None:
        """Updates info for branches."""
        # TODO: Change to new chunks if we have exceeded our size
        metadata_data_by_chunk: Dict[str, bytes] = {}
        branch_ids = (
            set(parents.keys())
            | set(children.keys())
            | set(tags.keys())
            | set(metadata.keys())
        )
        for branch_id in branch_ids:
            chunk_id = self._id_to_meta_compressor_map[branch_id]
            if chunk_id not in metadata_data_by_chunk:
                metadata_data_by_chunk[chunk_id] = b""
            metadata_data_by_chunk[chunk_id] += self._meta_compressors[chunk_id].add(
                branch_id=branch_id,
                parent=parents.get(branch_id),
                children=children.get(branch_id),
                tags=tags.get(branch_id),
                metadata=metadata.get(branch_id),
            )

        await self.bramble_backend.async_append_data(chunk_data=metadata_data_by_chunk)
