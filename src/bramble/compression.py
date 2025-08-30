from typing import Any, Set, Self

from dataclasses import dataclass

from bramble.logs import LogEntry, MessageType

import brotli
import msgpack


ENCODING_LENGTH_SIZE: int = 2


@dataclass
class CompressionWriter:
    compressor: Any
    assigned_branches: Set[str]
    assigned_names: Set[str]
    previous_branch: str
    data: bytes

    @classmethod
    def new(cls) -> Self:
        return CompressionWriter(
            brotli.Compressor(mode=brotli.MODE_TEXT, quality=11, lgwin=24, lgblock=0),
            set(),
            set(),
            None,
            b"",
        )

    def add(self, branch: str, entry: LogEntry):
        if not branch == self.previous_branch:
            self.data += (0).to_bytes(ENCODING_LENGTH_SIZE, "big")
            self.data += branch.encode()
            self.previous_branch = branch

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
    pass


class ChunkCompressor:
    def __init__(self, num_simultaneous_chunks: int = 8, chunk_size: int = 1):
        self.chunkers = [_Chunker.new() for _ in range(num_simultaneous_chunks)]


if __name__ == "__main__":
    example_entry = LogEntry(
        "Here is a message that we want to have saved and compressed, because otherwise our logs become too large and unweildy!",
        112340.2345,
        MessageType.USER,
        entry_metadata={
            "function": "my_very_special_function",
            "a key": "a value that includes a ,",
            "some integer": 1204,
            "some float": 1052.35235,
            "some bool": False,
        },
    )

    writer = CompressionWriter.new()
    writer.add("some branch", example_entry)
    print(writer.len())

    import json

    example_entry_dict = example_entry.as_dict()
    entry_string = json.dumps(example_entry_dict)
    entry_bytes = entry_string.encode()
    print(len(entry_bytes))

    msg_pack_bytes = msgpack.packb(
        (
            example_entry.timestamp,
            example_entry.message,
            example_entry.message_type.value,
            example_entry.entry_metadata,
        )
    )
    print(len(msg_pack_bytes))
