import pytest
from unittest.mock import AsyncMock, MagicMock

from bramble.loggers import TreeLogger, LogBranch
from bramble.backend import BrambleWriter
from bramble.logs import MessageType


class MockWriter(BrambleWriter):
    def __init__(self):
        self.async_append_entries = AsyncMock()
        self.async_update_tree = AsyncMock()
        self.async_update_branch_metadata = AsyncMock()
        self.async_add_tags = AsyncMock()


@pytest.fixture
def mock_backend():
    return MockWriter()


def test_logger_initializes_with_valid_backend(mock_backend):
    logger = TreeLogger(logging_backend=mock_backend, name="root")
    assert isinstance(logger.root, LogBranch)
    assert logger.root.name == "root"
    assert logger.logging_backend is mock_backend


def test_logger_rejects_invalid_backend():
    with pytest.raises(ValueError):
        TreeLogger(logging_backend="not-a-backend")


def test_branch_creation_and_linking(mock_backend):
    logger = TreeLogger(logging_backend=mock_backend)
    parent = logger.root
    child = parent.branch("child")

    assert isinstance(child, LogBranch)
    assert child.parent == parent.id
    assert child.id in parent.children
    assert child.name == "child"


def test_branch_logging_puts_task_in_queue(mock_backend):
    logger = TreeLogger(logging_backend=mock_backend)
    branch = logger.root

    logger._tasks = MagicMock()
    branch.log("A test log", message_type="USER")

    assert logger._tasks.put.called
    put_args = logger._tasks.put.call_args[0][0]
    assert put_args[0] == 0  # log task
    assert put_args[1] == branch.id


def test_add_tags_valid(mock_backend):
    logger = TreeLogger(logging_backend=mock_backend)
    branch = logger.root

    branch.add_tags(["tag1", "tag2"])
    assert "tag1" in branch.tags
    assert "tag2" in branch.tags


@pytest.mark.parametrize(
    "bad_tags",
    [
        "not-a-list",
        [123, "valid"],
        [None],
    ],
)
def test_add_tags_invalid(bad_tags, mock_backend):
    logger = TreeLogger(logging_backend=mock_backend)
    branch = logger.root

    with pytest.raises(ValueError):
        branch.add_tags(bad_tags)


def test_add_metadata_valid(mock_backend):
    logger = TreeLogger(logging_backend=mock_backend)
    branch = logger.root

    branch.add_metadata({"key": "value", "num": 123})
    assert branch.metadata["key"] == "value"
    assert branch.metadata["num"] == 123


@pytest.mark.parametrize(
    "bad_metadata",
    [
        "not-a-dict",
        {1: "bad key"},
        {"key": object()},
    ],
)
def test_add_metadata_invalid(bad_metadata, mock_backend):
    logger = TreeLogger(logging_backend=mock_backend)
    branch = logger.root

    with pytest.raises(ValueError):
        branch.add_metadata(bad_metadata)


def test_context_sets_and_clears_branch_context(mock_backend):
    from bramble.contextual import _CURRENT_BRANCH_IDS, _LIVE_BRANCHES

    logger = TreeLogger(logging_backend=mock_backend)
    with logger as ctx_logger:
        assert ctx_logger is logger
        current_ids = _CURRENT_BRANCH_IDS.get()
        assert logger.root.id in current_ids
        assert logger.root.id in _LIVE_BRANCHES

    # After context exit
    assert logger.root.id not in _CURRENT_BRANCH_IDS.get()
    assert logger.root.id not in _LIVE_BRANCHES


def test_log_entry_validation(mock_backend):
    logger = TreeLogger(logging_backend=mock_backend)
    branch = logger.root
    logger._tasks = MagicMock()

    branch.log("Test message", message_type=MessageType.USER, entry_metadata={"k": 1})
    call = logger._tasks.put.call_args[0][0]

    assert call[0] == 0
    assert isinstance(call[2].message, str)
    assert call[2].entry_metadata["k"] == 1


def test_add_child_and_set_parent_updates_backend(mock_backend):
    with TreeLogger(logging_backend=mock_backend) as logger:
        parent = logger.root
        child = parent.branch("child")  # Triggers both set_parent and add_child

    # After context exit, thread is guaranteed to have joined
    # We can only assume one call to the tree update, since the TreeLogger will
    # batch updates
    assert mock_backend.async_update_tree.call_count >= 1

    # Optional: inspect args
    calls = mock_backend.async_update_tree.call_args_list
    for call in calls:
        relationships = call[1]["relationships"]
        assert isinstance(relationships, dict)
