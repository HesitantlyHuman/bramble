import pytest
from datetime import datetime
import dataclasses

from bramble.logs import MessageType, LogEntry, BranchData


def test_message_type_from_valid_strings():
    assert MessageType.from_string("system") == MessageType.SYSTEM
    assert MessageType.from_string(" USER  ") == MessageType.USER
    assert MessageType.from_string("Error") == MessageType.ERROR


def test_message_type_from_invalid_string():
    with pytest.raises(ValueError):
        MessageType.from_string("invalid")


def test_message_type_from_non_string():
    with pytest.raises(ValueError):
        MessageType.from_string(123)


def test_log_entry_fields_are_set_correctly():
    entry = LogEntry(
        message="Test message",
        timestamp=1234567890.0,
        message_type=MessageType.USER,
        entry_metadata={"key": "value", "num": 42, "flag": True},
    )

    assert entry.message == "Test message"
    assert entry.timestamp == 1234567890.0
    assert entry.message_type == MessageType.USER
    assert entry.entry_metadata == {"key": "value", "num": 42, "flag": True}


def test_branch_data_fields_are_set_correctly():
    entry = LogEntry(
        message="msg",
        timestamp=123.0,
        message_type=MessageType.SYSTEM,
        entry_metadata={},
    )

    branch = BranchData(
        id="abc",
        name="branch",
        parent=None,
        children=["child1", "child2"],
        messages=[entry],
        tags=["tag1", "tag2"],
        metadata={"foo": "bar"},
    )

    assert branch.id == "abc"
    assert branch.name == "branch"
    assert branch.parent is None
    assert branch.children == ["child1", "child2"]
    assert branch.messages == [entry]
    assert branch.tags == ["tag1", "tag2"]
    assert branch.metadata == {"foo": "bar"}


def test_log_entry_and_branch_data_are_immutable():
    entry = LogEntry(
        message="immutable",
        timestamp=0.0,
        message_type=MessageType.USER,
        entry_metadata={},
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.message = "changed"

    branch = BranchData(
        id="id",
        name="name",
        parent=None,
        children=[],
        messages=[],
        tags=[],
        metadata={},
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        branch.name = "new_name"


def test_log_entry_serialization_and_deserialization():
    entry = LogEntry(
        message="Test message",
        timestamp=1234.56,
        message_type=MessageType.SYSTEM,
        entry_metadata={"key": "value", "num": 42},
    )
    as_dict = entry.as_dict()
    expected = {
        "message": "Test message",
        "timestamp": 1234.56,
        "message_type": "system",
        "entry_metadata": {"key": "value", "num": 42},
    }
    assert as_dict == expected

    reconstructed = LogEntry.from_dict(as_dict)
    assert reconstructed == entry


def test_log_entry_serialization_with_none_metadata():
    entry = LogEntry(
        message="Hello",
        timestamp=0.1,
        message_type=MessageType.ERROR,
        entry_metadata=None,
    )
    d = entry.as_dict()
    assert "entry_metadata" not in d
    assert d["message_type"] == "error"

    reconstructed = LogEntry.from_dict(
        {"message": "Hello", "timestamp": 0.1, "message_type": "error"}
    )
    assert reconstructed == entry


def test_log_entry_from_dict_invalid_input_type():
    with pytest.raises(ValueError, match="must be a dictionary"):
        LogEntry.from_dict("not a dict")


def test_log_entry_from_dict_missing_keys():
    with pytest.raises(ValueError, match="must have keys .* 'timestamp'"):
        LogEntry.from_dict({"message": "Hello", "message_type": "user"})


def test_branch_data_serialization_and_deserialization():
    now = datetime.now()
    log = LogEntry(
        message="Nested",
        timestamp=now,
        message_type=MessageType.USER,
        entry_metadata=None,
    )
    branch = BranchData(
        id="abc123",
        name="root",
        parent=None,
        children=["child1"],
        messages=[log],
        tags=["important"],
        metadata={"level": 1},
    )

    as_dict = branch.as_dict()
    expected = {
        "id": "abc123",
        "name": "root",
        "parent": None,
        "children": ["child1"],
        "messages": [log.as_dict()],
        "tags": ["important"],
        "metadata": {"level": 1},
    }
    assert as_dict == expected

    reconstructed = BranchData.from_dict(as_dict)
    assert reconstructed == branch


def test_branch_data_from_dict_invalid_input_type():
    with pytest.raises(ValueError, match="must be a dictionary"):
        BranchData.from_dict(["not", "a", "dict"])


def test_branch_data_from_dict_missing_keys():
    with pytest.raises(ValueError, match="must have keys .* 'children'"):
        BranchData.from_dict(
            {
                "id": "1",
                "name": "test",
                "parent": None,
                "messages": [],
                "tags": [],
                "metadata": {},
            }
        )


def test_branch_data_from_dict_invalid_messages():
    with pytest.raises(ValueError, match="'messages' entry .* must be a list"):
        BranchData.from_dict(
            {
                "id": "1",
                "name": "test",
                "parent": None,
                "children": [],
                "messages": "not a list",
                "tags": [],
                "metadata": {},
            }
        )
