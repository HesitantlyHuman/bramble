from typing import Dict, List, Tuple

from lumberjack.logs import LogEntry, BranchData


class LumberjackWriter:
    """Writing backend interface for `lumberjack` logging.

    Users who wish to extend the capabilities of lumberjack and use different
    storage backends for their logs should implement the functions of this
    interface.

    IMPORTANT: For each function pair (sync and async) you only need implement
    one of the given functions. Internally, lumberjack will always call the async
    function, but the default behavior of the async functions is to call their
    sync counterparts.

    For example, you only need to implement either `append_entries` or implement
    `async_append_entries`, but not both. `lumberjack` logging and the `lumberjack` ui
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


class LumberjackReader:
    """Reading backend interface for `lumberjack` logging.

    Users who wish to extend the capabilities of lumberjack and use different
    storage backends for their logs should implement the functions of this
    interface.

    IMPORTANT: For each function pair (sync and async) you only need implement
    one of the given functions. Internally, lumberjack will always call the async
    function, but the default behavior of the async functions is to call their
    sync counterparts.

    For example, you only need to implement either `get_branches` or implement
    `async_get_branches`, but not both. `lumberjack` logging and the `lumberjack` ui
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
