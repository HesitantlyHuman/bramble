from typing import Mapping, Sequence, Generator, Protocol, runtime_checkable

import io


@runtime_checkable
class ByteSource(Protocol):
    def read(self, n: int = -1) -> bytes: ...


def as_byte_source(x: bytes | bytearray | memoryview | ByteSource) -> ByteSource:
    if isinstance(x, ByteSource):
        return x
    return io.BytesIO(bytes(x))


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

    def get_branch_ids(
        self, start: int = 0, stop: int = None
    ) -> Generator[str, None, None]:
        """Get branch IDs from the master list.

        Gets the most recent branch IDs from the master list. If `stop` is
        `None`, `get_branch_ids` will get all of the branch IDs from the master
        list, starting from `start`.

        Args:
            start (int): Index of the first ID to retrieve.
            stop (int): Index of the last ID to retrieve.

        Returns:
            (Generator[str, None, None]): A generator yielding the ordered
                branch IDs.
        """
        raise NotImplementedError(f"{type(self)} does not implement `get_branch_ids`!")

    async def async_get_branch_ids(
        self, start: int = 0, stop: int = None
    ) -> Generator[str, None, None]:
        """Get branch IDs from the master list.

        Gets the most recent branch IDs from the master list. If `stop` is
        `None`, `async_get_branch_ids` will get all of the branch IDs from the
        master list, starting from `start`.

        Args:
            start (int): Index of the first ID to retrieve.
            stop (int): Index of the last ID to retrieve.

        Returns:
            (Generator[str, None, None]): A generator yielding the ordered
                branch IDs.
        """
        return self.get_branch_ids(start=start, stop=stop)

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
