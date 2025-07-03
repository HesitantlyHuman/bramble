from typing import Dict, List, Self

from dataclasses import dataclass
from enum import Enum


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


@dataclass(frozen=True, slots=True)
class LogEntry:
    """A log entry for a tree logger."""

    message: str
    timestamp: float
    message_type: MessageType
    entry_metadata: Dict[str, str | int | float | bool]


@dataclass(frozen=True, slots=True)
class BranchData:
    """A tree logger branch's full info."""

    id: str
    name: str
    parent: str | None
    children: List[str]
    messages: List[LogEntry]
    tags: List[str]
    metadata: Dict[str, str | int | float | bool]
