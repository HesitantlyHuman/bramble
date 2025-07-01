from typing import Any, Dict, List, Tuple


from treelog.logs import LogEntry, BranchData

# TODO: maybe merge these?

# TODO: update docstrings


# TODO: Document the fact that you only need to implement either the sync or
# async version of any of the backend methods.
class TreeLogWriter:
    def append_entries(
        self,
        entries: Dict[str, List[LogEntry]],
    ) -> None:
        """Append log entries to the tree logger storage.

        Args:
            log_entries (Dict[str, List[LogEntry]]): The log entries to append, keyed by branch id.
        """
        raise NotImplementedError()

    async def async_append_entries(
        self,
        entries: Dict[str, List[LogEntry]],
    ) -> None:
        """Append log entries to the tree logger storage.

        Args:
            log_entries (Dict[str, List[LogEntry]]): The log entries to append, keyed by branch id.
        """
        self.append_entries(entries=entries)

    def add_tags(self, tags: Dict[str, List[str]]) -> None:
        """Add tags to tree logger branches.

        Does not remove existing tags. Does not add duplicate tags.

        Args:
            tags (Dict[str, List[str]]): The tags to add, keyed by branch id.
        """
        raise NotImplementedError()

    async def async_add_tags(self, tags: Dict[str, List[str]]) -> None:
        """Add tags to tree logger branches.

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
        """Update the parent and children relationships for multiple tree logger branches.

        If there is existing relationship data, it should be overwritten.

        Args:
            relationships (Dict[str, Tuple[str | None, List[str]]]):
                Mapping of branch IDs to a `(parent_id, list_of_child_ids)` tuple.
                The parent ID can be `None` for root nodes.
        """
        raise NotImplementedError()

    async def async_update_tree(
        self, relationships: Dict[str, Tuple[str | None, List[str]]]
    ) -> None:
        """Update the parent and children relationships for multiple tree logger branches.

        If there is existing relationship data, it should be overwritten.

        Args:
            relationships (Dict[str, Tuple[str | None, List[str]]]):
                Mapping of branch IDs to a `(parent_id, list_of_child_ids)` tuple.
                The parent ID can be `None` for root nodes.
        """
        self.update_tree(relationships=relationships)

    def update_branch_metadata(
        self, metadata: Dict[str, Dict[str, str | int | float | bool]]
    ) -> None:
        """Updates the metadata for tree logger branches with an arbitrary dictionary.

        Creates metadata if it does not exist. If the new metadata is a subset of the
        existing metadata, only the keys provided in the new metadata will be updated.

        Args:
            metadata (Dict[str, Dict[str, str | int | float | bool]]): Mapping of branch IDs to a metadata dictionary.
        """
        raise NotImplementedError()

    async def async_update_branch_metadata(
        self, metadata: Dict[str, Dict[str, str | int | float | bool]]
    ) -> None:
        """Updates the metadata for tree logger branches with an arbitrary dictionary.

        Creates metadata if it does not exist. If the new metadata is a subset of the
        existing metadata, only the keys provided in the new metadata will be updated.

        Args:
            metadata (Dict[str, Dict[str, str | int | float | bool]]): Mapping of branch IDs to a metadata dictionary.
        """
        self.update_branch_metadata(metadata=metadata)


class TreeLogReader:
    def get_branches(self, branch_ids: List[str]) -> Dict[str, BranchData]:
        """Get the data for tree logger branches.

        Args:
            branch_ids (List[str]): The IDs of the tree logger branches.

        Returns:
            Dict[str, BranchData]: A dict of branch IDs to the corresponding BranchData
                object.
        """
        raise NotImplementedError()

    async def async_get_branches(self, branch_ids: List[str]) -> Dict[str, BranchData]:
        """Get the data for tree logger branches.

        Args:
            branch_ids (List[str]): The IDs of the tree logger branches.

        Returns:
            Dict[str, BranchData]: A dict of branch IDs to the corresponding BranchData
                object.
        """
        return self.get_branches(branch_ids=branch_ids)

    def get_branch_ids(self) -> List[str]:
        """Get the IDs of all tree logger branches.

        Returns:
            List[str]: The IDs of all tree logger branches.
        """
        raise NotImplementedError()

    async def async_get_branch_ids(self) -> List[str]:
        """Get the IDs of all tree logger branches.

        Returns:
            List[str]: The IDs of all tree logger branches.
        """
        return self.get_branch_ids()
