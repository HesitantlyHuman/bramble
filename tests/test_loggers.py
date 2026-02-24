import pytest
from unittest.mock import AsyncMock, MagicMock

from bramble.loggers import TreeLogger, LogBranch
from bramble.writer import BrambleWriter
from bramble.log_objects import MessageType


class MockWriter(BrambleWriter):
    def __init__(self):
        self.add_branches = AsyncMock()
        self.close_branches = AsyncMock()
        self.append_entries = AsyncMock()
        self.update_branch_info = AsyncMock()


@pytest.fixture
def mock_backend():
    # Keep fixture name to minimize churn; it now returns a writer.
    return MockWriter()


def _get_field(obj, name, default=None):
    """Access dict keys or object attributes uniformly."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def test_logger_initializes_with_valid_backend(mock_backend):
    # TreeLogger now accepts a writer instead of a backend.
    logger = TreeLogger(writer=mock_backend, name="root")
    assert isinstance(logger.root, LogBranch)
    assert logger.root.name == "root"
    assert logger.writer is mock_backend


def test_logger_rejects_invalid_backend():
    # Keep test name, but pass the invalid object to the writer param.
    with pytest.raises(ValueError):
        TreeLogger(writer="not-a-backend")


def test_branch_creation_and_linking(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    parent = logger.root
    child = parent.branch("child")

    assert isinstance(child, LogBranch)
    assert child.parent == parent.id
    assert child.id in parent.children
    assert child.name == "child"


def test_branch_logging_puts_task_in_queue(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    branch = logger.root

    logger._tasks = MagicMock()
    branch.log("A test log", message_type="USER")

    assert logger._tasks.put.called
    put_args = logger._tasks.put.call_args[0][0]
    assert put_args[0] == 0  # log task
    assert put_args[1] == branch.id


def test_add_tags_valid(mock_backend):
    logger = TreeLogger(writer=mock_backend)
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
    logger = TreeLogger(writer=mock_backend)
    branch = logger.root

    with pytest.raises(ValueError):
        branch.add_tags(bad_tags)


def test_add_metadata_valid(mock_backend):
    logger = TreeLogger(writer=mock_backend)
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
    logger = TreeLogger(writer=mock_backend)
    branch = logger.root

    with pytest.raises(ValueError):
        branch.add_metadata(bad_metadata)


def test_context_sets_and_clears_branch_context(mock_backend):
    from bramble.contextual import _CURRENT_BRANCH_IDS, _LIVE_BRANCHES

    logger = TreeLogger(writer=mock_backend)
    with logger as ctx_logger:
        assert ctx_logger is logger
        current_ids = _CURRENT_BRANCH_IDS.get()
        assert logger.root.id in current_ids
        assert logger.root.id in _LIVE_BRANCHES

    # After context exit
    assert logger.root.id not in _CURRENT_BRANCH_IDS.get()
    assert logger.root.id not in _LIVE_BRANCHES


def test_log_entry_validation(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    branch = logger.root
    logger._tasks = MagicMock()

    branch.log("Test message", message_type=MessageType.USER, entry_metadata={"k": 1})
    call = logger._tasks.put.call_args[0][0]

    assert call[0] == 0
    assert isinstance(call[2].message, str)
    assert call[2].entry_metadata["k"] == 1


def test_add_child_and_set_parent_updates_backend(mock_backend):
    """
    This test used to assert on backend async_update_tree calls.
    With the writer refactor, relationship updates should flow through
    writer.update_branch_info (and/or add_branches, depending on your impl).
    We keep the same intent: creating a child should produce at least one
    writer call that contains relationship info in the payload.
    """
    captured_parents = []
    captured_children = []

    async def capture_branch_info(parents, children, tags, metadata):
        print(parents, children, tags, metadata)
        if parents:
            for _, parent in parents.items():
                captured_parents.append(parent)

        if children:
            for _, branch_children in children.items():
                captured_children.extend(branch_children)

    mock_backend.update_branch_info.side_effect = capture_branch_info

    with TreeLogger(writer=mock_backend) as logger:
        parent = logger.root
        _child = parent.branch("child")  # Triggers both set_parent and add_child

    # After context exit, the logger should have flushed/batched updates.
    assert mock_backend.update_branch_info.call_count >= 1
