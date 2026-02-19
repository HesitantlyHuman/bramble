from typing import Mapping, Sequence, Tuple

from bramble.logs import LogEntry, BranchData


class BrambleBackend:
    """Backend interface for `bramble` logging.

    Users who wish to extend the capabilities of bramble and use different
    storage backends for their logs should implement the functions of this
    interface.

    IMPORTANT: For each function pair (sync and async) you only need implement
    *one* of the given functions. Internally, bramble will always call the async
    function, but the default behavior of the async functions is to call their
    sync counterparts.

    For example, you only need to implement either `append_entries` or implement
    `async_append_entries`, but not both. `bramble` logging and the `bramble` UI
    will work as long as either is implemented.
    """

    # TODO: How to we separate the tree data (the parent and child relationships between calls) from the metadata?
    # What if a user wants to add a field called parent, or child? (Just name the fields `bramble_parent` and `bramble_children`)

    def append_data(self, chunk_data: Mapping[str, bytes]) -> Mapping[str, int]:
        """Appends data to chunks.

        If `append_data` receives a new chunk ID, then that chunk should be
        created, and then the relevant bytes appended.

        Args:
            chunk_data (Mapping[str, bytes]): Bytes to append, keyed by chunk
                ID.

        Returns:
            (Mapping[str, int]): Total bytes of the chunk, after appending,
                keyed by chunk ID.
        """
        raise NotImplementedError(f"{type(self)} does not implement `append_data`!")

    async def async_append_data(
        self, chunk_data: Mapping[str, bytes]
    ) -> Mapping[str, int]:
        """Appends data to chunks.

        If `async_append_data` receives a new chunk ID, then that chunk should
        be created, and then the relevant bytes appended.

        Args:
            chunk_data (Mapping[str, bytes]): Bytes to append, keyed by chunk
                ID.

        Returns:
            (Mapping[str, int]): Total bytes of the chunk, after appending,
                keyed by chunk ID.
        """
        return self.append_data(chunk_data=chunk_data)

    def assign_chunks(
        self, branch_chunks: Mapping[str, Sequence[str]], chunk_type: str
    ) -> None:
        """Assigns chunks to branches.

        Accepts a `chunk_type` argument, used for separating different types of
        chunks (such as log entries vs metadata), so that these types can be
        read independently. For example, we may want to only load the metadata
        for a given branch, if we are searching over our branches.

        Args:
            branch_chunks (Mapping[str, Sequence[str]]): Chunk IDs to assign to
                each branch, keyed by branch ID.
            chunk_type (str): The type of data stored in these chunks.
        """
        raise NotImplementedError(f"{type(self)} does not implement `assign_chunks`!")

    async def async_assign_chunks(
        self, branch_chunks: Mapping[str, Sequence[str]], chunk_type: str
    ) -> None:
        """Assigns chunks to branches.

        Accepts a `chunk_type` argument, used for separating different types of
        chunks (such as log entries vs metadata), so that these types can be
        read independently. For example, we may want to only load the metadata
        for a given branch, if we are searching over our branches.

        Args:
            branch_chunks (Mapping[str, Sequence[str]]): Chunk IDs to assign to
                each branch, keyed by branch ID.
            chunk_type (str): The type of data stored in these chunks.
        """
        return self.assign_chunks(branch_chunks=branch_chunks, chunk_type=chunk_type)

    def add_branches(self, branch_ids: Sequence[str]) -> None:
        """Adds branch IDs to the master list.

        Args:
            branch_ids (Sequence[str]): The branch IDs which should be appended
                to the master list.
        """
        raise NotImplementedError(f"{type(self)} does not implement `add_branches`!")

    async def async_add_branches(self, branch_ids: Sequence[str]) -> None:
        """Adds branch IDs to the master list.

        Args:
            branch_ids (Sequence[str]): The branch IDs which should be appended
                to the master list.
        """
        return self.add_branches(branch_ids=branch_ids)

    def set_active_chunks(self, chunk_ids: Sequence[str]) -> None:
        """Sets the active chunks.

        `set_active_chunks` will replace the existing active chunks. Ensure that
        you provide all of the chunks IDs you wish to mark active.

        Args:
            chunk_ids (Sequence[str]): The IDs of the currently active chunks.
        """
        raise NotImplementedError(
            f"{type(self)} does not implement `set_active_chunks`!"
        )

    async def async_set_active_chunks(self, chunk_ids: Sequence[str]) -> None:
        """Sets the active chunks.

        `async_set_active_chunks` will replace the existing active chunks.
        Ensure that you provide all of the chunks IDs you wish to mark active.

        Args:
            chunk_ids (Sequence[str]): The IDs of the currently active chunks.
        """
        return self.set_active_chunks(chunk_ids=chunk_ids)

    def get_branch_ids(self, num_ids: int = None) -> Sequence[str]:
        """Get branch IDs from the master list.

        Gets the most recent `num_ids` branch IDs from the master list. If
        `num_ids` is `None`, `get_branch_ids` will get all of the branch IDs
        from the master list.

        Args:
            num_ids (int): The number of IDs to get from the master list.
        """
        raise NotImplementedError(f"{type(self)} does not implement `get_branch_ids`!")

    async def async_get_branch_ids(self, num_ids: int = None) -> Sequence[str]:
        """Get branch IDs from the master list.

        Gets the most recent `num_ids` branch IDs from the master list. If
        `num_ids` is `None`, `async_get_branch_ids` will get all of the branch
        IDs from the master list.

        Args:
            num_ids (int): The number of IDs to get from the master list.
        """
        return self.get_branch_ids(num_ids=num_ids)

    def get_chunk_ids(
        self, branch_ids: Sequence[str], type: str
    ) -> Mapping[str, Sequence[str]]:
        """Gets the IDs of chunks associated with branches.

        Gets the IDs of chunks which contain data from each of the given
        branches, and are of the provided type.

        Args:
            branch_ids (Sequence[str]): The branch IDs to get chunk IDs for.
            type (str): The type of chunks to return IDs for.

        Returns:
            (Mapping[str, Sequence[str]]): A mapping from the provided branch
                IDs, to a sequence of associated chunk IDs.
        """
        raise NotImplementedError(f"{type(self)} does not implement `get_chunk_ids`!")

    async def async_get_chunk_ids(
        self, branch_ids: Sequence[str], type: str
    ) -> Mapping[str, Sequence[str]]:
        """Gets the IDs of chunks associated with branches.

        Gets the IDs of chunks which contain data from each of the given
        branches, and are of the provided type.

        Args:
            branch_ids (Sequence[str]): The branch IDs to get chunk IDs for.
            type (str): The type of chunks to return IDs for.

        Returns:
            (Mapping[str, Sequence[str]]): A mapping from the provided branch
                IDs, to a sequence of associated chunk IDs.
        """
        return self.get_chunk_ids(branch_ids=branch_ids, type=type)

    def get_data(self, chunk_ids: Sequence[str]) -> Mapping[str, bytes]:
        """Gets the chunk data of the provided IDs.

        Args:
            chunk_ids (Sequence[str]): The chunk IDs to get data for.

        Returns:
            (Mapping[str, bytes]): A mapping from the provided chunk IDs, to the
                data of each chunk.
        """
        raise NotImplementedError(f"{type(self)} does not implement `get_data`!")

    async def async_get_data(self, chunk_ids: Sequence[str]) -> Mapping[str, bytes]:
        """Gets the chunk data of the provided IDs.

        Args:
            chunk_ids (Sequence[str]): The chunk IDs to get data for.

        Returns:
            (Mapping[str, bytes]): A mapping from the provided chunk IDs, to the
                data of each chunk.
        """
        return self.get_data(chunk_ids=chunk_ids)

    def get_active_chunks(self) -> Sequence[str]:
        """Gets the active chunks.

        Returns:
            (Sequence[str]): A sequence of the chunk IDs for the currently
                active chunks.
        """
        raise NotImplementedError(
            f"{type(self)} does not implement `get_active_chunks`!"
        )

    async def async_get_active_chunks(self) -> Sequence[str]:
        """Gets the active chunks.

        Returns:
            (Sequence[str]): A sequence of the chunk IDs for the currently
                active chunks.
        """
        return self.get_active_chunks()


# TODO: create a `BrambleBackend` class to replace this
class BrambleWriter:
    """Writing backend interface for `bramble` logging.

    Users who wish to extend the capabilities of bramble and use different
    storage backends for their logs should implement the functions of this
    interface.

    IMPORTANT: For each function pair (sync and async) you only need implement
    one of the given functions. Internally, bramble will always call the async
    function, but the default behavior of the async functions is to call their
    sync counterparts.

    For example, you only need to implement either `append_entries` or implement
    `async_append_entries`, but not both. `bramble` logging and the `bramble` ui
    will work as long as either is implemented.
    """

    def append_entries(
        self,
        entries: Dict[str, List[LogEntry]],
    ) -> None:
        """Appends log entries to the tree logger storage.

        Args:
            log_entries (Dict[str, List[LogEntry]]): The log entries to append,
            keyed by branch id.
        """
        raise NotImplementedError()

    async def async_append_entries(
        self,
        entries: Dict[str, List[LogEntry]],
    ) -> None:
        """Appends log entries to the tree logger storage.

        Args:
            log_entries (Dict[str, List[LogEntry]]): The log entries to append,
            keyed by branch id.
        """
        self.append_entries(entries=entries)

    def add_tags(self, tags: Dict[str, List[str]]) -> None:
        """Adds tags to tree logger branches.

        Does not remove existing tags. Does not add duplicate tags.

        Args:
            tags (Dict[str, List[str]]): The tags to add, keyed by branch id.
        """
        raise NotImplementedError()

    async def async_add_tags(self, tags: Dict[str, List[str]]) -> None:
        """Adds tags to tree logger branches.

        Does not remove existing tags. Does not add duplicate tags.

        Args:
            tags (Dict[str, List[str]]): The tags to add, keyed by branch id.
        """
        self.add_tags(tags=tags)

    def remove_tags(self, tags: Dict[str, List[str]]) -> None:
        """Removes tags from tree logger branches.

        If a tag does not exist, it is ignored.

        Args:
            tags (Dict[str, List[str]]): The tags to remove, keyed by branch id.
        """
        raise NotImplementedError()

    async def async_remove_tags(self, tags: Dict[str, List[str]]) -> None:
        """Removes tags from tree logger branches.

        If a tag does not exist, it is ignored.

        Args:
            tags (Dict[str, List[str]]): The tags to remove, keyed by branch id.
        """
        self.remove_tags(tags=tags)

    def update_tree(
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
        raise NotImplementedError()

    async def async_update_tree(
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
        self.update_tree(relationships=relationships)

    def update_branch_metadata(
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
        raise NotImplementedError()

    async def async_update_branch_metadata(
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
        self.update_branch_metadata(metadata=metadata)


class BrambleReader:
    """Reading backend interface for `bramble` logging.

    Users who wish to extend the capabilities of bramble and use different
    storage backends for their logs should implement the functions of this
    interface.

    IMPORTANT: For each function pair (sync and async) you only need implement
    one of the given functions. Internally, bramble will always call the async
    function, but the default behavior of the async functions is to call their
    sync counterparts.

    For example, you only need to implement either `get_branches` or implement
    `async_get_branches`, but not both. `bramble` logging and the `bramble` ui
    will work as long as either is implemented.
    """

    def get_branches(self, branch_ids: List[str]) -> Dict[str, BranchData]:
        """Gets the data for tree logger branches.

        Args:
            branch_ids (List[str]): The IDs of the tree logger branches.

        Returns:
            Dict[str, BranchData]: A dict of branch IDs to the corresponding
                BranchData object.
        """
        raise NotImplementedError()

    async def async_get_branches(self, branch_ids: List[str]) -> Dict[str, BranchData]:
        """Gets the data for tree logger branches.

        Args:
            branch_ids (List[str]): The IDs of the tree logger branches.

        Returns:
            Dict[str, BranchData]: A dict of branch IDs to the corresponding
                BranchData object.
        """
        return self.get_branches(branch_ids=branch_ids)

    def get_branch_ids(self) -> List[str]:
        """Gets the IDs of all tree logger branches.

        Returns:
            List[str]: The IDs of all tree logger branches.
        """
        raise NotImplementedError()

    async def async_get_branch_ids(self) -> List[str]:
        """Gets the IDs of all tree logger branches.

        Returns:
            List[str]: The IDs of all tree logger branches.
        """
        return self.get_branch_ids()
