from typing import Dict, List, Self, Any

from dataclasses import dataclass, asdict
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
    entry_metadata: Dict[str, str | int | float | bool] | None

    def as_dict(self) -> Dict[str, Any]:
        dictionary = asdict(self)
        dictionary["message_type"] = dictionary["message_type"].value
        if dictionary["entry_metadata"] is None:
            del dictionary["entry_metadata"]
        return dictionary

    @classmethod
    def from_dict(cls, dictionary: Dict[str, Any]) -> Self:
        if not isinstance(dictionary, dict):
            raise ValueError(
                f"`dictionary` must be a dictionary, received {type(dictionary)}."
            )
        for key in ["message", "timestamp", "message_type"]:
            if not key in dictionary:
                raise ValueError(
                    f"`dictionary` must have keys ['message', 'timestamp', 'message_type'], received {list(dictionary.keys())}."
                )
        if not "entry_metadata" in dictionary:
            dictionary["entry_metadata"] = None
        dictionary["message_type"] = MessageType.from_string(dictionary["message_type"])

        return cls(**dictionary)


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

    def as_dict(self) -> Dict[str, Any]:
        dictionary_messages = [message.as_dict() for message in self.messages]
        dictionary = asdict(self)
        dictionary["messages"] = dictionary_messages
        return dictionary

    @classmethod
    def from_dict(cls, dictionary: Dict[str, Any]) -> Self:
        if not isinstance(dictionary, dict):
            raise ValueError(
                f"`dictionary` must be a dictionary, received {type(dictionary)}."
            )
        for key in ["id", "name", "parent", "children", "messages", "tags", "metadata"]:
            if not key in dictionary:
                raise ValueError(
                    f"`dictionary` must have keys ['id', 'name', 'parent', 'children', 'messages', 'tags', 'metadata'], received {list(dictionary.keys())}."
                )
        if not isinstance(dictionary["messages"], list):
            raise ValueError(
                f"'messages' entry of `dictionary` must be a list, received {type(dictionary['messages'])}"
            )
        dictionary["messages"] = [
            LogEntry.from_dict(log_dict) for log_dict in dictionary["messages"]
        ]
        return cls(**dictionary)
