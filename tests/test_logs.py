import pytest

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
