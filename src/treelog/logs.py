from typing import Dict, List, Self
from dataclasses import dataclass
from enum import Enum

# TODO: create custom serialization and deserialization


class MessageType(Enum):
    """The type of a tree logger log message."""

    SYSTEM = "system"
    ERROR = "error"
    USER = "user"

    @classmethod
    def from_string(cls, input: str) -> Self | None:
        try:
            return cls(input.lower().strip())
        except:
            raise ValueError(f"'{input}' is not a valid MessageType!")


@dataclass
class LogEntry:
    """A log entry for a tree logger."""

    message: str
    timestamp: float
    message_type: MessageType
    entry_metadata: Dict[str, str | int | float | bool]

    def __dict__(self):
        return {
            "message": self.message,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
            "entry_metadata": self.entry_metadata,
        }


@dataclass
class TreeLog:
    """A tree logger's full info."""

    id: str
    messages: List[LogEntry]
    metadata: Dict[str, str | int | float | bool]
    tags: List[str]

    def __dict__(self):
        return {
            "id": self.id,
            "messages": self.messages,
            "metadata": self.metadata,
            "tags": self.tags,
        }
