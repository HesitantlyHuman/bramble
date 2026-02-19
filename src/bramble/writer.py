from typing import Dict, List, Tuple

import asyncio

from bramble.logs import LogEntry
from bramble.compression import ChunkCompressor
from bramble.backends import BrambleBackend


class BrambleWriter:
    chunk_compressor: ChunkCompressor
    bramble_backend: BrambleBackend

    def __init__(
        self,
        bramble_backend: BrambleBackend,
        num_simultaneous_chunks: int = 8,
        chunk_size: int = 2**32,
    ):
        self.bramble_backend
        self.chunk_compressor = ChunkCompressor(
            num_simultaneous_chunks=num_simultaneous_chunks, chunk_size=chunk_size
        )

    async def append_entries(
        self,
        entries: Dict[str, List[LogEntry]],
    ) -> None:
        """Appends log entries to the tree logger storage.

        Args:
            log_entries (Dict[str, List[LogEntry]]): The log entries to append,
            keyed by branch id.
        """
        chunk_writing_tasks = []
        for branch_id, log_entries in entries.items():
            for log_entry in log_entries:
                # TODO: how do we get information about the name of the branch here?
                output = self.chunk_compressor.add(
                    branch_id=branch_id, branch_name="uh oh", entry=log_entry
                )
                if not output is None:
                    # TODO: how do we know which ids went in this chunk?
                    # Maybe the chunk compressor should return that
                    chunk_writing_tasks.append(
                        self.bramble_backend.async_write_chunk(output)
                    )

        await asyncio.gather(*chunk_writing_tasks)

    async def add_tags(self, tags: Dict[str, List[str]]) -> None:
        """Adds tags to tree logger branches.

        Does not remove existing tags. Does not add duplicate tags.

        Args:
            tags (Dict[str, List[str]]): The tags to add, keyed by branch id.
        """
        await self.bramble_backend.async_add_tags(tags=tags)

    async def update_tree(
        self, relationships: Dict[str, Tuple[str | None, List[str]]]
    ) -> None:
        """Updates parent and child relationships for tree logger branches.

        If there is existing relationship data, it will be overwritten. For
        example, if there is an existing child which is not provided as input
        in `relationships`, that branch will be removed as a child of the
        appropriate parent branch.

        Args:
            relationships (Dict[str, Tuple[str | None, List[str]]]):
                Mapping of branch IDs to a `(parent_id, list_of_child_ids)`
                tuple. The parent ID can be `None` for root nodes.
        """
        await self.bramble_backend.async_update_tree(relationships=relationships)

    async def update_branch_metadata(
        self, metadata: Dict[str, Dict[str, str | int | float | bool]]
    ) -> None:
        """Updates metadata for tree logger branches.

        Creates metadata if it does not exist. If the new metadata is a subset
        of the existing metadata, only the keys provided in the new metadata
        will be updated, and other keys will keep their existing values.

        Args:
            metadata (Dict[str, Dict[str, str | int | float | bool]]): Mapping
                of branch IDs to metadata dictionaries.
        """
        await self.bramble_backend.async_update_branch_metadata(metadata=metadata)
