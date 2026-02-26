from typing import Dict, List, Tuple, Set, Any, Iterable, Callable

import asyncio
import datetime

from bramble.utils import _generate_id
from bramble.log_objects import LogEntry
from bramble.backends.base import BrambleBackend
from bramble.compression import EntryCompressor, MetadataCompressor, BrambleCompressor


# TODO: Add support for loading the active chunks
class BrambleWriter:
    """A compressing log writer for bramble logs.

    The BrambleWriter is a compressing interface between bramble logging and the
    BrambleBackends. The writer will dynamically assign branches to chunks, and
    compress incoming log data. The writer will then add this data to the
    backend storage as it goes.

    Attributes:
        num_simultaneous_chunks (int): How many chunks the writer will write to
            in parallel. Increasing the number of chunks will incur overhead,
            but decrease the number of chunks that branches are spread across,
            and improve branch name affinity within chunks.
        chunk_size (int): Target number of bytes per chunk. If the chunk is
            larger than this value, the writer will rotate to a new chunk.
        compression_quality (int): An integer between 0 and 11 which sets the
            compression quality, with 0 being the fastest, and 11 being the
            most compressed.
        max_assignment_imbalance_factor (float): How many times more branches
            assigned to it a chunk can have than the least assigned to chunk,
            before the writer will break name affinity.
        base_assignment_imbalance_num (int): Base number of assignments before
            the writer will consider chunk branch assignment imbalance.
    """

    backend: BrambleBackend
    num_simultaneous_chunks: int
    chunk_size: int
    compression_quality: int
    max_assignment_imbalance_factor: float
    base_assignment_imbalance_num: int

    def __init__(
        self,
        backend: BrambleBackend,
        num_simultaneous_chunks: int = 32,
        chunk_size_mb: float = 16.0,
        compression_quality: int = 6,
        max_assignment_imbalance_factor: float = 3.0,
        base_assignment_imbalance_num: int = 10,
    ):
        if not isinstance(backend, BrambleBackend):
            raise ValueError(
                f"`backend` must be of type `BrambleBackend`, received {type(backend)}."
            )

        if not isinstance(max_assignment_imbalance_factor, (int, float)):
            raise ValueError(
                f"`max_assignment_imbalance_factor` must be of type `int` or `float`, received {type(max_assignment_imbalance_factor)}."
            )

        if not isinstance(base_assignment_imbalance_num, (int, float)):
            raise ValueError(
                f"`base_assignment_imbalance_num` must be of type `int` or `float`, received {type(base_assignment_imbalance_num)}."
            )

        if base_assignment_imbalance_num < 1:
            raise ValueError(
                f"`base_assignment_imbalance_num` must be at least 1, received: {base_assignment_imbalance_num}"
            )

        self.backend = backend
        self.num_simultaneous_chunks = num_simultaneous_chunks
        self.chunk_size = int(chunk_size_mb * 1024 * 1024)
        self.max_assignment_imbalance_factor = max_assignment_imbalance_factor
        self.base_assignment_imbalance_num = base_assignment_imbalance_num
        self.compression_quality = compression_quality

        self._entry_compressors = {
            _generate_id("ec"): EntryCompressor.new(quality=compression_quality)
            for _ in range(self.num_simultaneous_chunks)
        }
        self._meta_compressors = {
            _generate_id("mc"): MetadataCompressor.new(quality=compression_quality)
            for _ in range(self.num_simultaneous_chunks)
        }

        self._id_to_entry_compressor_map: Dict[str, str] = {}
        self._id_to_meta_compressor_map: Dict[str, str] = {}

        self._name_to_entry_compressor_map: Dict[str, Set[str]] = {}
        self._name_to_meta_compressor_map: Dict[str, Set[str]] = {}

        self._entry_chunk_to_ids_and_names: Dict[int, Set[Tuple[str, str]]] = {
            chunk_id: set() for chunk_id in self._entry_compressors.keys()
        }
        self._meta_chunk_to_ids_and_names: Dict[int, Set[Tuple[str, str]]] = {
            chunk_id: set() for chunk_id in self._meta_compressors.keys()
        }

        self._entry_chunk_assignment_options: Set[str] = set(
            self._entry_compressors.keys()
        )
        self._meta_chunk_assignment_options: Set[str] = set(
            self._meta_compressors.keys()
        )

        self._chunk_sizes: Dict[str, int] = {
            chunk_id: 0
            for chunk_id in set(self._entry_compressors.keys())
            | set(self._meta_compressors.keys())
        }

        self._active_branches_calculated_metadata: Dict[str, Dict[str, Any]] = {}

    def _assignment_helper(
        self,
        branch_id: str,
        name: str,
        compressors: Dict[str, BrambleCompressor],
        id_to_compressor_map: Dict[str, str],
        name_to_compressor_map: Dict[str, Set[str]],
        chunk_to_ids_and_names: Dict[int, Set[Tuple[str, str]]],
        chunk_assignment_options: Set[str],
    ) -> str:
        current_num_assignments = {
            chunk_id: len(vals) for chunk_id, vals in chunk_to_ids_and_names.items()
        }
        max_entry_allowed = int(
            (
                min([0] + list(current_num_assignments.values()))
                + self.base_assignment_imbalance_num
            )
            * self.max_assignment_imbalance_factor
        )
        if len(chunk_assignment_options) == 0:
            chunk_assignment_options.update(compressors.keys())

        # First, attempt to assign by name, then, just assign to any chunk
        for compressor_candidates in [
            name_to_compressor_map.get(name),
            chunk_assignment_options,
        ]:
            if compressor_candidates is not None:
                selected_id, selected_num_assignments = min(
                    [
                        (candidate, current_num_assignments[candidate])
                        for candidate in compressor_candidates
                    ],
                    key=lambda x: x[1],
                )
                if selected_num_assignments <= max_entry_allowed:
                    id_to_compressor_map[branch_id] = selected_id
                    name_to_compressor_map.setdefault(name, set()).add(selected_id)
                    chunk_to_ids_and_names[selected_id].add((branch_id, name))
                    try:
                        # If we are assigning by name, then we may have already
                        # removed this chunk from the candidate pool.
                        chunk_assignment_options.remove(selected_id)
                    except KeyError:
                        pass
                    return selected_id

        raise RuntimeError(f"Reached unexpected termination condition!")

    def _assign_chunk(self, branch_id: str, name: str) -> Tuple[str, str]:
        """Assigns branches to chunks."""
        return (
            self._assignment_helper(
                branch_id=branch_id,
                name=name,
                compressors=self._entry_compressors,
                id_to_compressor_map=self._id_to_entry_compressor_map,
                name_to_compressor_map=self._name_to_entry_compressor_map,
                chunk_to_ids_and_names=self._entry_chunk_to_ids_and_names,
                chunk_assignment_options=self._entry_chunk_assignment_options,
            ),
            self._assignment_helper(
                branch_id=branch_id,
                name=name,
                compressors=self._meta_compressors,
                id_to_compressor_map=self._id_to_meta_compressor_map,
                name_to_compressor_map=self._name_to_meta_compressor_map,
                chunk_to_ids_and_names=self._meta_chunk_to_ids_and_names,
                chunk_assignment_options=self._meta_chunk_assignment_options,
            ),
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
        """Adds new branches to the backend storage.

        Assigns branches to chunks, then adds the new chunk assignments and
        branches to the backend storage. Attempts to make assignments for
        branches based on name affinity, so that compression ratios are
        improved, but will spread the assignment of open branches around to
        minimize the number of branches per chunk.

        Args:
            ids_and_names (Set[Tuple[str, str]]): A set of the branch IDs and
                names to be added to the backend.
        """
        entry_chunk_assignments, meta_chunk_assignments = self._assign_chunks(
            ids_and_names=ids_and_names
        )
        ids_to_add = {id for id, _ in ids_and_names}
        for branch_id in ids_to_add:
            self._active_branches_calculated_metadata[branch_id] = {
                "created": datetime.datetime.now().timestamp(),
                "started": None,
                "stopped": None,
                "num_entries": 0,
            }
        master_list_task = self.backend.async_add_branches(ids_to_add)
        entry_assignment_task = self.backend.async_assign_chunks(
            branch_chunks=entry_chunk_assignments, chunk_type="ec"
        )
        meta_assignment_task = self.backend.async_assign_chunks(
            branch_chunks=meta_chunk_assignments, chunk_type="mc"
        )

        await asyncio.gather(
            master_list_task, entry_assignment_task, meta_assignment_task
        )

    def _close_branch(self, branch_id: str) -> bool:
        """Mark branch as closed."""
        has_updated = False
        try:
            assigned_entry_chunk = self._id_to_entry_compressor_map[branch_id]
            del self._id_to_entry_compressor_map[branch_id]
            self._entry_chunk_to_ids_and_names[assigned_entry_chunk] = {
                item
                for item in self._entry_chunk_to_ids_and_names[assigned_entry_chunk]
                if item[0] == branch_id
            }
            has_updated = True
        except KeyError:
            pass

        try:
            assigned_meta_chunk = self._id_to_meta_compressor_map[branch_id]
            del self._id_to_meta_compressor_map[branch_id]
            self._meta_chunk_to_ids_and_names[assigned_meta_chunk] = {
                item
                for item in self._meta_chunk_to_ids_and_names[assigned_meta_chunk]
                if item[0] == branch_id
            }
            has_updated = True
        except KeyError:
            pass

        try:
            del self._active_branches_calculated_metadata[branch_id]
        except KeyError:
            pass

        return has_updated

    async def close_branches(self, branch_ids: Set[str]) -> None:
        """Mark branches as closed.

        Closes branches and removes mappings. Allows the writer to better track
        how many active branches are assigned to each chunk.

        Args:
            branch_ids (Set[str]): The ids of the branches which are closed.
        """
        # First, let's collect the calculated metadata that we need to write out
        calculated_metadata_output = {}
        for branch_id in branch_ids:
            try:
                calculated_metadata_output[branch_id] = (
                    self._active_branches_calculated_metadata[branch_id]
                )
            except KeyError:
                pass

        # Then write the metadata out
        await self.update_branch_info(
            parents=None, children=None, tags=None, metadata=calculated_metadata_output
        )

        # Now, we will update our internal representations, to remove those branches
        has_updated = False
        for branch_id in branch_ids:
            if self._close_branch(branch_id=branch_id):
                has_updated = True

        if has_updated:
            self._name_to_entry_compressor_map: Dict[str, Set[str]] = {}
            self._name_to_meta_compressor_map: Dict[str, Set[str]] = {}

            for chunk_id, ids_and_names in self._entry_chunk_to_ids_and_names.items():
                for _, name in ids_and_names:
                    self._name_to_entry_compressor_map.setdefault(name, set()).add(
                        chunk_id
                    )

            for chunk_id, ids_and_names in self._meta_chunk_to_ids_and_names.items():
                for _, name in ids_and_names:
                    self._name_to_meta_compressor_map.setdefault(name, set()).add(
                        chunk_id
                    )

    async def _build_and_write_chunks(
        self,
        item_iterable: Iterable[Tuple[str, Any]],
        compression_function: Callable[[str, str, Any], bytes],
        compressor_creation_function: Callable[[], Tuple[str, BrambleCompressor]],
        compressors: Dict[str, BrambleCompressor],
        id_to_compressor_map: Dict[str, str],
        name_to_compressor_map: Dict[str, Set[str]],
        chunk_to_ids_and_names: Dict[str, Set[Tuple[str, str]]],
    ) -> Dict[str, bytes]:
        chunk_ids_to_cleanup: Set[str] = set()
        logging_data_by_chunk: Dict[str, bytes] = {}
        for branch_id, item in item_iterable:
            chunk_id = id_to_compressor_map[branch_id]
            next_bytes = compression_function(chunk_id, branch_id, item)
            logging_data_by_chunk.setdefault(chunk_id, b"")
            logging_data_by_chunk[chunk_id] += next_bytes

            # If we are already over the chunk size, or if receiving another
            # similarly sized chunk would put us over the chunk size, then we
            # will move to a new chunk.
            if (
                len(logging_data_by_chunk[chunk_id])
                + self._chunk_sizes[chunk_id]
                + len(next_bytes)
                >= self.chunk_size
            ):
                chunk_ids_to_cleanup.add(chunk_id)
                new_chunk_id, new_compressor = compressor_creation_function()
                compressors[new_chunk_id] = new_compressor
                chunk_to_ids_and_names[new_chunk_id] = chunk_to_ids_and_names[chunk_id]
                for id_to_transfer, name_to_transfer in chunk_to_ids_and_names[
                    new_chunk_id
                ]:
                    id_to_compressor_map[id_to_transfer] = new_chunk_id
                    name_to_compressor_map[name_to_transfer].remove(chunk_id)
                    name_to_compressor_map[name_to_transfer].add(new_chunk_id)

        chunk_sizes = await self.backend.async_append_data(
            chunk_data=logging_data_by_chunk
        )
        self._chunk_sizes.update(chunk_sizes)

        for chunk_id in chunk_ids_to_cleanup:
            del compressors[chunk_id]
            del chunk_to_ids_and_names[chunk_id]
            del self._chunk_sizes[chunk_id]

    async def append_entries(
        self,
        entries: Dict[str, List[LogEntry]],
    ) -> None:
        """Appends log entries to the tree logger storage.

        Compresses the provided log entries, and then writes the new bytes to
        the assigned chunks in the backend.

        Args:
            log_entries (Dict[str, List[LogEntry]]): The log entries to append,
            keyed by branch id.
        """
        # Update the branches' calculated metadata
        for branch_id, branch_entries in entries.items():
            entry_timestamps = [entry.timestamp for entry in branch_entries]
            self._active_branches_calculated_metadata[branch_id]["num_entries"] += 1
            if self._active_branches_calculated_metadata[branch_id]["started"] is None:
                self._active_branches_calculated_metadata[branch_id]["started"] = min(
                    entry_timestamps
                )
            self._active_branches_calculated_metadata[branch_id]["stopped"] = max(
                entry_timestamps
            )

        def _compress(chunk_id: str, branch_id: str, log_entry: LogEntry) -> bytes:
            return self._entry_compressors[chunk_id].add(
                branch_id=branch_id, entry=log_entry
            )

        def _create_compressor() -> Tuple[str, EntryCompressor]:
            return _generate_id("ec"), EntryCompressor.new(
                quality=self.compression_quality
            )

        await self._build_and_write_chunks(
            item_iterable=iter(entries.items()),
            compression_function=_compress,
            compressor_creation_function=_create_compressor,
            compressors=self._entry_compressors,
            id_to_compressor_map=self._id_to_entry_compressor_map,
            name_to_compressor_map=self._name_to_entry_compressor_map,
            chunk_to_ids_and_names=self._entry_chunk_to_ids_and_names,
        )

    async def update_branch_info(
        self,
        parents: Dict[str, str] | None,
        children: Dict[str, Set[str]] | None,
        tags: Dict[str, Set[str]] | None,
        metadata: Dict[str, Dict[str, str | int | float | bool]] | None,
    ) -> None:
        """Updates info for branches.

        Compresses the provided branch info, and then writes the new bytes to
        the assigned chunks in the backend.

        Args:
            parents (Dict[str, str]): The parent updates to apply. A mapping of
                branch IDs to parent branch IDs.
            children (Dict[str, Set[str]]): The children to add. A mapping of
                branch IDs to new children branch IDs.
            tags (Dict[str, Set[str]]): The tags to add. A mapping of branch IDs
                to new tags.
            metadata (Dict[str, Dict[str, Any]]): The metadata updates to apply.
                A mapping of branch IDs to branch metadata.
        """
        if parents is None:
            parents = {}
        if children is None:
            children = {}
        if tags is None:
            tags = {}
        if metadata is None:
            metadata = {}

        branch_ids = (
            set(parents.keys())
            | set(children.keys())
            | set(tags.keys())
            | set(metadata.keys())
        )

        def _iterable():
            for branch_id in branch_ids:
                yield (
                    branch_id,
                    (
                        parents.get(branch_id),
                        children.get(branch_id),
                        tags.get(branch_id),
                        metadata.get(branch_id),
                    ),
                )

        def _compress(chunk_id: str, branch_id: str, branch_info: tuple) -> bytes:
            parent, children, tags, metadata = branch_info
            return self._meta_compressors[chunk_id].add(
                branch_id=branch_id,
                parent=parent,
                children=children,
                tags=tags,
                metadata=metadata,
            )

        def _create_compressor() -> Tuple[str, MetadataCompressor]:
            return _generate_id("mc"), MetadataCompressor.new(
                quality=self.compression_quality
            )

        await self._build_and_write_chunks(
            item_iterable=_iterable(),
            compression_function=_compress,
            compressor_creation_function=_create_compressor,
            compressors=self._meta_compressors,
            id_to_compressor_map=self._id_to_meta_compressor_map,
            name_to_compressor_map=self._name_to_meta_compressor_map,
            chunk_to_ids_and_names=self._meta_chunk_to_ids_and_names,
        )
