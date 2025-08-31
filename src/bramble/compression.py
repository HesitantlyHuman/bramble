from typing import Any, Set, Self, Tuple, Generator, Dict

from dataclasses import dataclass

from bramble.logs import LogEntry, MessageType

import brotli
import msgpack


ENCODING_LENGTH_SIZE: int = 2


@dataclass
class CompressionWriter:
    compressor: Any
    data: bytes

    _previous_branch_id: str

    @classmethod
    def new(cls) -> Self:
        return CompressionWriter(
            brotli.Compressor(
                mode=brotli.MODE_TEXT,
                quality=11,
                lgwin=24,
                lgblock=0,
            ),
            set(),
            set(),
            b"",
            None,
        )

    def add(self, branch_id: str, entry: LogEntry):
        if not branch_id == self._previous_branch_id:
            self.data += (0).to_bytes(ENCODING_LENGTH_SIZE, "big")
            compressed_branch = (
                self.compressor.process(branch_id.encode()) + self.compressor.flush()
            )
            self.data += len(compressed_branch).to_bytes(ENCODING_LENGTH_SIZE, "big")
            self.data += compressed_branch
            self._previous_branch_id = branch_id

        compressed_message = (
            self.compressor.process(entry.message.encode()) + self.compressor.flush()
        )
        self.data += len(compressed_message).to_bytes(ENCODING_LENGTH_SIZE, "big")
        self.data += compressed_message

        compressed_timestamp = (
            self.compressor.process(str(entry.timestamp).encode())
            + self.compressor.flush()
        )
        self.data += len(compressed_timestamp).to_bytes(ENCODING_LENGTH_SIZE, "big")
        self.data += compressed_timestamp

        match entry.message_type:
            case MessageType.SYSTEM:
                self.data += (0).to_bytes(1, "big")
            case MessageType.USER:
                self.data += (1).to_bytes(1, "big")
            case MessageType.ERROR:
                self.data += (1).to_bytes(1, "big")

        if entry.entry_metadata is None:
            self.data += (0).to_bytes(ENCODING_LENGTH_SIZE, "big")
            return

        formatted_metadata = msgpack.packb(entry.entry_metadata)
        compressed_metadata = (
            self.compressor.process(formatted_metadata) + self.compressor.flush()
        )
        self.data += len(compressed_metadata).to_bytes(ENCODING_LENGTH_SIZE, "big")
        self.data += compressed_metadata

    def len(self) -> int:
        return len(self.data)


@dataclass
class CompressionReader:
    decompressor: Any
    data: bytes

    _read_position: int
    _previous_branch_id: str

    @classmethod
    def from_bytes(cls, input_bytes: bytes) -> Self:
        return CompressionReader(brotli.Decompressor(), input_bytes, 0, None)

    def _consume(self, num_bytes: int) -> bytes | None:
        if self._read_position >= len(self.data):
            return None
        chunk = self.data[self._read_position : self._read_position + num_bytes]
        self._read_position += num_bytes
        return chunk

    def _read_single(self) -> Tuple[str, LogEntry]:
        initial = self._consume(ENCODING_LENGTH_SIZE)
        if initial is None:
            return None

        initial_value = int.from_bytes(initial, "big")
        if initial_value == 0:
            # Read out the branch id, because we are getting a new one
            branch_id_length = int.from_bytes(
                self._consume(ENCODING_LENGTH_SIZE), "big"
            )
            branch_id_compressed = self._consume(branch_id_length)
            branch_id = self.decompressor.process(branch_id_compressed).decode()
            self._previous_branch_id = branch_id

            # Reset the message length
            message_length = int.from_bytes(self._consume(ENCODING_LENGTH_SIZE), "big")
        else:
            branch_id = self._previous_branch_id
            message_length = initial_value

        # Read the message
        message_compressed = self._consume(message_length)
        message = self.decompressor.process(message_compressed).decode()

        # Read the timestamp
        timestamp_length = int.from_bytes(self._consume(ENCODING_LENGTH_SIZE), "big")
        timestamp_compressed = self._consume(timestamp_length)
        timestamp = float(self.decompressor.process(timestamp_compressed).decode())

        # Read the message type
        match int.from_bytes(self._consume(1), "big"):
            case 0:
                message_type = MessageType.SYSTEM
            case 1:
                message_type = MessageType.USER
            case 2:
                message_type = MessageType.ERROR

        # Read the metadata
        metadata_length = int.from_bytes(self._consume(ENCODING_LENGTH_SIZE), "big")
        if metadata_length == 0:
            metadata = None
        else:
            compressed_metadata = self._consume(metadata_length)
            metadata = msgpack.loads(self.decompressor.process(compressed_metadata))

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
        next_item = self._read_single()

        while next_item is not None:
            yield next_item
            next_item = self._read_single()


class ChunkCompressor:
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

    example_entry = LogEntry(
        """Here is a message that we want to have saved and compressed, because otherwise our logs become too large and unwieldy! Here is a message that we want to have saved and compressed, because otherwise our logs become too large and unwieldy!""",
        112340.2345,
        MessageType.USER,
        entry_metadata=None,
    )

    writer = CompressionWriter.new()
    id = _generate_id()
    print(id)
    l = 0
    writer.add(id, "", example_entry)
    print(writer.len() - l)
    l = writer.len()
    writer.add(id, "", example_entry)
    print(writer.len() - l)
    l = writer.len()
    writer.add(id, "", example_entry)
    print(writer.len() - l)
    l = writer.len()
    writer.add(id, "", example_entry)
    print(writer.len() - l)
    l = writer.len()
    id = _generate_id()
    print(id)
    writer.add(id, "", example_entry)
    print(writer.len() - l)
    l = writer.len()
    writer.add(id, "", example_entry)
    print(writer.len() - l)
    l = writer.len()

    reader = CompressionReader.from_bytes(writer.data)
    for branch_id, log_entry in reader.read():
        print(branch_id, log_entry)
