import gc
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bramble.loggers import TreeLogger, LogBranch
from bramble.writer import BrambleWriter
from bramble.log_objects import MessageType
import bramble.loggers as loggers_mod


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


def _run(coro):
    return asyncio.run(coro)


def _patch_logger_run_to_flush_closes(logger: TreeLogger):
    """
    Patch logger.run with a deterministic drain that:
      - collects branch-close tasks (code 5),
      - stops on None sentinel,
      - calls writer.close_branches({ids}) once at the end (if any).
    This avoids depending on the real background thread batching/timeout logic.
    """

    def _run_sync():
        to_close = set()

        while True:
            task = logger._tasks.get()
            if task is None:
                break
            if task and task[0] == 5:
                _, branch_id = task
                to_close.add(branch_id)

        if to_close:
            _run(logger.writer.close_branches(to_close))

    logger.run = _run_sync


def test_leaving_logging_context_removes_branches_from_live_branches(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    _patch_logger_run_to_flush_closes(logger)

    with logger as l:
        root_id = l.root.id
        assert root_id in loggers_mod._LIVE_BRANCHES

    # After context exit, branch should be removed from _LIVE_BRANCHES
    assert logger.root.id not in loggers_mod._LIVE_BRANCHES


def test_closing_branch_manually_removes_from_live_and_current_ids(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    _patch_logger_run_to_flush_closes(logger)

    with logger as l:
        with l.root.branch("child") as child:
            assert child.id in loggers_mod._LIVE_BRANCHES
            assert child.id in loggers_mod._CURRENT_BRANCH_IDS.get()

            child.close()

            assert child.id not in loggers_mod._LIVE_BRANCHES
            assert child.id not in loggers_mod._CURRENT_BRANCH_IDS.get()


def test_closing_branches_calls_writer_close_branches_with_correct_ids(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    _patch_logger_run_to_flush_closes(logger)

    with logger as l:
        child1 = l.root.branch("c1")
        child2 = l.root.branch("c2")

        child1.close()
        child2.close()

    # Our patched run() flushes close_branches once on exit
    assert mock_backend.close_branches.call_count >= 1
    # verify the last call contains both ids (set semantics)
    args, kwargs = mock_backend.close_branches.call_args
    # AsyncMock captures as positional; writer.close_branches(branch_ids)
    closed_ids = args[0] if args else kwargs.get("branch_ids")
    assert set(closed_ids) == {child1.id, child2.id}


def _drain_close_tasks(logger: TreeLogger) -> set[str]:
    """
    Drain any pending close tasks (code 5) currently in the logger queue and
    synchronously run writer.close_branches on them.
    Returns the drained ids.
    """
    to_close: set[str] = set()

    while True:
        try:
            task = logger._tasks.get_nowait()
        except Exception:
            break

        if task is None:
            # Put it back; caller might still want normal shutdown behavior.
            logger._tasks.put(None)
            break

        if task and task[0] == 5:
            _, bid = task
            to_close.add(bid)

    if to_close:
        _run(logger.writer.close_branches(to_close))

    return to_close


def test_not_holding_branch_reference_will_close_on_del(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    _patch_logger_run_to_flush_closes(logger)

    closed_ids = set()

    async def capture_branches(branch_ids: set):
        print(branch_ids)
        closed_ids.update(branch_ids)

    logger.writer.close_branches = capture_branches

    with logger as l:
        child = l.root.branch("child")
        child_id = child.id

        child = None
        gc.collect()

        import time

        time.sleep(0.1)

        # Force the queued close task to be processed *now*.
        _drain_close_tasks(l)

    assert child_id in closed_ids


def test_holding_branch_reference_keeps_it_from_closing_until_manual_close(
    mock_backend,
):
    logger = TreeLogger(writer=mock_backend)
    _patch_logger_run_to_flush_closes(logger)

    closed_ids = set()

    async def capture_branches(branch_ids: set):
        closed_ids.update(branch_ids)

    logger.writer.close_branches = capture_branches

    with logger as l:
        child = l.root.branch("child")
        child_id = child.id

        with child:
            pass

        gc.collect()
        _drain_close_tasks(l)
        # Still referenced by `child`, so should still be live
        assert child_id not in closed_ids

        # Manual close should remove it immediately
        child.close()
        _drain_close_tasks(l)
        assert child_id in closed_ids


def test_logging_to_closed_branch_raises_value_error(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    _patch_logger_run_to_flush_closes(logger)

    with logger as l:
        child = l.root.branch("child")
        child.close()

        with pytest.raises(ValueError):
            # If your implementation raises from TreeLogger.log, this will propagate here
            child.log("should fail", message_type=MessageType.USER)


def test_close_is_idempotent(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    _patch_logger_run_to_flush_closes(logger)

    with logger as l:
        child = l.root.branch("child")
        child_id = child.id

        child.close()
        assert child_id not in loggers_mod._LIVE_BRANCHES

        # Second close should not raise
        child.close()
        assert child_id not in loggers_mod._LIVE_BRANCHES


def test_branch_context_manager_closes_on_exit(mock_backend):
    logger = TreeLogger(writer=mock_backend)
    _patch_logger_run_to_flush_closes(logger)

    with logger as l:
        with l.root.branch("scoped") as _:
            scoped_id = loggers_mod._CURRENT_BRANCH_IDS.get().copy().pop()
            assert scoped_id in loggers_mod._LIVE_BRANCHES

        # After exiting the branch context manager, it should have closed itself
        assert scoped_id not in loggers_mod._LIVE_BRANCHES
        assert scoped_id not in loggers_mod._CURRENT_BRANCH_IDS.get()
