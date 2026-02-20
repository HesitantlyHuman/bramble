from typing import Any, Set, Self, Tuple, Generator, Dict, List

from dataclasses import dataclass

import brotli
import msgpack

from bramble.log_objects import LogEntry, MessageType
from bramble.backends.base import ByteSource, as_byte_source

PREFIX_SIZE: int = 2


def _pack_compress_flush(compressor: Any, input: Any) -> bytes:
    data = b""

    match input:
        case str():
            packed = input.encode()
        case _:
            packed = msgpack.packb(input)

    compressed = compressor.process(packed) + compressor.flush()
    data += len(compressed).to_bytes(PREFIX_SIZE, "big")
    data += compressed
    return data


@dataclass
class Writer:
    compressor: Any

    _previous_branch_id: str

    @classmethod
    def new(cls) -> Self:
        return cls(
            brotli.Compressor(
                mode=brotli.MODE_TEXT,
                quality=11,
                lgwin=24,
                lgblock=0,
            ),
            None,
        )

    def add(*args, **kwargs) -> bytes: ...


@dataclass
class Reader:
    decompressor: Any
    byte_source: ByteSource

    _previous_branch_id: str

    @classmethod
    def new(cls, byte_source: ByteSource | bytes | bytearray | memoryview) -> Self:
        byte_source = as_byte_source(byte_source)
        return cls(brotli.Decompressor(), byte_source, None)

    def _read_and_decompress_next_chunk(self) -> bytes:
        prefix_bytes = self.byte_source.read(PREFIX_SIZE)
        if len(prefix_bytes) == 0:
            raise EOFError(f"Unexpected end of byte stream.")

        chunk_length = int.from_bytes(prefix_bytes, "big")
        compressed = self.byte_source.read(chunk_length)
        if len(compressed) < chunk_length:
            raise EOFError(f"Unexpected end of byte stream.")
        uncompressed = self.decompressor.process(compressed)
        return uncompressed


class MetadataWriter(Writer):
    def add(
        self,
        branch_id: str,
        parent: str = None,
        children: List[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, str | int | float | bool] = None,
    ) -> bytes:
        data = b""

        if not branch_id == self._previous_branch_id:
            data += (0).to_bytes(1, "big")
            data += _pack_compress_flush(self.compressor, branch_id)
            self._previous_branch_id = branch_id

        if parent is not None:
            data += (1).to_bytes(1, "big")
            data += _pack_compress_flush(self.compressor, parent)

        if children is not None and len(children) > 0:
            children = list(set(children))
            data += (2).to_bytes(1, "big")
            data += _pack_compress_flush(self.compressor, children)

        if tags is not None and len(tags) > 0:
            tags = list(set(tags))
            data += (3).to_bytes(1, "big")
            data += _pack_compress_flush(self.compressor, tags)

        if metadata is not None and len(metadata) > 0:
            data += (4).to_bytes(1, "big")
            data += _pack_compress_flush(self.compressor, metadata)

        return data


class EntryWriter(Writer):
    def add(self, branch_id: str, entry: LogEntry) -> bytes:
        data = b""

        if not branch_id == self._previous_branch_id:
            data += (0).to_bytes(PREFIX_SIZE, "big")
            data += _pack_compress_flush(self.compressor, branch_id)
            self._previous_branch_id = branch_id

        match entry.message_type:
            case MessageType.SYSTEM:
                encoded_message_type = 0
            case MessageType.USER:
                encoded_message_type = 1
            case MessageType.ERROR:
                encoded_message_type = 2

        data += _pack_compress_flush(
            self.compressor,
            (
                entry.message,
                entry.timestamp,
                encoded_message_type,
                entry.entry_metadata,
            ),
        )
        return data


# TODO: The return values here seem kinda dumb.... maybe we should be collecting here?
class MetadataReader(Reader):
    def read_next(
        self,
    ) -> Tuple[
        str,
        str | None,
        List[str] | None,
        List[str] | None,
        Dict[str, str | int | float | bool] | None,
    ]:
        # Get the initial branch id if we have not already
        if self._previous_branch_id is None:
            type_bytes = self.byte_source.read(1)
            if len(type_bytes) == 0:
                return None
            type_value = int.from_bytes(type_bytes, "big")
            if not type_value == 0:
                raise ValueError(
                    f"Expected data stream to start with branch ID (code 0), started with code: {type_value}."
                )
            branch_id = self._read_and_decompress_next_chunk().decode()
            self._previous_branch_id = branch_id

        parent, children, tags, metadata = None, set(), set(), {}
        type_bytes = self.byte_source.read(1)
        if len(type_bytes) == 0:
            return None

        type_value = int.from_bytes(type_bytes, "big")

        while True:
            match type_value:
                case 0:
                    next_branch_id = self._read_and_decompress_next_chunk().decode()
                    output = (
                        self._previous_branch_id,
                        parent,
                        children,
                        tags,
                        metadata,
                    )
                    self._previous_branch_id = next_branch_id
                    return output
                case 1:
                    parent = self._read_and_decompress_next_chunk().decode()
                case 2:
                    new_children_bytes = self._read_and_decompress_next_chunk()
                    new_children = msgpack.loads(new_children_bytes)
                    children.update(set(new_children))
                case 3:
                    new_tag_bytes = self._read_and_decompress_next_chunk()
                    new_tags = msgpack.loads(new_tag_bytes)
                    tags.update(set(new_tags))
                case 4:
                    new_metadata_bytes = self._read_and_decompress_next_chunk()
                    new_metadata = msgpack.loads(new_metadata_bytes)
                    metadata.update(new_metadata)
                case _:
                    raise ValueError(
                        f"Received unknown code, expected 0-4, got {type_value}"
                    )
            type_bytes = self.byte_source.read(1)
            if len(type_bytes) == 0:
                # If we don't have any type bytes, then this is the end of the stream
                output = (self._previous_branch_id, parent, children, tags, metadata)
                self._previous_branch_id = None
                return output
            type_value = int.from_bytes(type_bytes, "big")

    def read(self) -> Generator[
        Tuple[
            str,
            str | None,
            List[str] | None,
            List[str] | None,
            Dict[str, str | int | float | bool] | None,
        ],
        None,
        None,
    ]:
        next_item = self.read_next()

        while next_item is not None:
            yield next_item
            next_item = self.read_next()


class EntryReader(Reader):
    def read_next(self) -> Tuple[str, LogEntry]:
        initial = self.byte_source.read(PREFIX_SIZE)
        if len(initial) == 0:
            return None

        initial_value = int.from_bytes(initial, "big")
        if initial_value == 0:
            # Read out the branch id, because we are getting a new one
            branch_id = self._read_and_decompress_next_chunk().decode()
            self._previous_branch_id = branch_id

            # Get the next value for the entry length
            entry_length = int.from_bytes(self.byte_source.read(PREFIX_SIZE), "big")
        else:
            branch_id = self._previous_branch_id
            entry_length = initial_value

        # Read the entry
        compressed_entry = self.byte_source.read(entry_length)
        if len(compressed_entry) < entry_length:
            raise EOFError(f"Unexpected end of byte stream!")
        uncompressed_entry = self.decompressor.process(compressed_entry)
        (message, timestamp, encoded_message_type, metadata) = msgpack.loads(
            uncompressed_entry
        )

        match encoded_message_type:
            case 0:
                message_type = MessageType.SYSTEM
            case 1:
                message_type = MessageType.USER
            case 2:
                message_type = MessageType.ERROR

        # Return our result
        return (
            branch_id,
            LogEntry(
                message=message,
                timestamp=timestamp,
                message_type=message_type,
                entry_metadata=metadata,
            ),
        )

    def read(self) -> Generator[Tuple[str, LogEntry], None, None]:
        next_item = self.read_next()

        while next_item is not None:
            yield next_item
            next_item = self.read_next()


class ChunkCompressor:
    # TODO: when we do the assignments we should pop from a list, so that we ensure we are using all of our active chunks. Then when we create a new list, we order it by the current size. Or, we have a list and we get the one from the list which is smallest currently, then pop.
    def __init__(self, num_simultaneous_chunks: int = 8, chunk_size: int = 2**32):
        self.num_simultaneous_chunks = num_simultaneous_chunks
        self.compressors = [
            CompressionWriter.new() for _ in range(num_simultaneous_chunks)
        ]
        self.chunk_size = chunk_size

        self.id_to_compressor_map: Dict[str, int] = (
            {}
        )  # This will need to be saved in the db
        self.name_to_compressor_map: Dict[str, int] = {}
        self.compressor_to_names_and_ids: Dict[int, Tuple[Set[str], Set[str]]] = {}

    def _get_or_assign_compressor(self, branch_id: str, branch_name: str) -> int:
        # First, identify if we have already assigned this branch_id
        if branch_id in self.id_to_compressor_map:
            return self.id_to_compressor_map[branch_id]

        # Otherwise, check if we have already assigned this name
        if branch_name in self.name_to_compressor_map:
            # Assign this branch id to the same compressor
            assigned_compressor = self.name_to_compressor_map[branch_name]
            self.id_to_compressor_map[branch_id] = assigned_compressor
            # Update the compressor map with the branch id
            self.compressor_to_names_and_ids[assigned_compressor][1].add(branch_id)
            return assigned_compressor

        # Otherwise, just assign this to the smallest current compressor
        assigned_compressor = min(
            range(len(self.compressors)), key=lambda x: self.compressors[x].len()
        )
        self.id_to_compressor_map[branch_id] = assigned_compressor
        self.name_to_compressor_map[branch_name] = assigned_compressor
        self.compressor_to_names_and_ids[assigned_compressor][0].add(branch_name)
        self.compressor_to_names_and_ids[assigned_compressor][1].add(branch_id)
        return assigned_compressor

    def _maybe_write_chunk(self, compressor_id: int) -> None | bytes:
        if self.compressors[compressor_id].len() < self.chunk_size:
            return None

        chunk = self.compressors[compressor_id].data

        names, ids = self.compressor_to_names_and_ids[compressor_id]
        del self.compressor_to_names_and_ids[compressor_id]

        for name in names:
            del self.name_to_compressor_map[name]

        for id in ids:
            del self.id_to_compressor_map[id]

        self.compressors[compressor_id] = CompressionWriter.new()

        return chunk

    def add(self, branch_id: str, branch_name: str, entry: LogEntry) -> None | bytes:
        compressor_id = self._get_or_assign_compressor(
            branch_id=branch_id, branch_name=branch_name
        )
        self.compressors[compressor_id].add(branch_id=branch_id, entry=entry)
        return self._maybe_write_chunk(compressor_id=compressor_id)


if __name__ == "__main__":
    from bramble.utils import _generate_id

    # example_entry = LogEntry(
    #     """Here is a message that we want to have saved and compressed, because otherwise our logs become too large and unwieldy! Here is a message that we want to have saved and compressed, because otherwise our logs become too large and unwieldy!""",
    #     112340.2345,
    #     MessageType.USER,
    #     entry_metadata=None,
    # )

    # data = b""
    # writer = EntryWriter.new()
    # id = _generate_id()
    # print(id)

    # for _ in range(3):
    #     next_bytes = writer.add(id, example_entry)
    #     data += next_bytes
    #     print(len(next_bytes))

    # id = _generate_id()
    # for _ in range(2):
    #     next_bytes = writer.add(id, example_entry)
    #     data += next_bytes
    #     print(len(next_bytes))

    # reader = EntryReader.new(data)
    # for branch_id, log_entry in reader.read():
    #     print(branch_id, log_entry)

    writer = MetadataWriter.new()

    data = b""
    id = _generate_id()
    data += writer.add(
        id,
        "parent",
        ["a", "b", "c"],
        ["tag_a", "tag-b"],
        {"key": "value", "another": 235},
    )
    data += writer.add(
        id,
        None,
        ["d"],
        None,
        {"another": 244},
    )
    print(len(data))
    data += writer.add(
        _generate_id(),
        "parent",
        ["a", "b", "c"],
        ["tag_a", "tag-b"],
        {"key": "value", "another": 235},
    )
    print(len(data))
    data += writer.add(
        _generate_id(),
        "parent",
        ["a", "b", "c"],
        ["tag_a", "tag-b"],
        {"key": "value", "another": 235},
    )
    print(len(data))

    reader = MetadataReader.new(data)
    for output in reader.read():
        print(output)
