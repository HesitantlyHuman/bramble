import asyncio
import pytest

from unittest.mock import AsyncMock
from contextlib import nullcontext

from bramble.contextual import log, apply, context, disable, enable, fork
from bramble.utils import _stringify_function_call
from bramble.writer import BrambleWriter
from bramble.log_objects import MessageType, LogEntry
from bramble.loggers import TreeLogger, LogBranch
from bramble.wrapper import branch


# ----------------------------
# Test helpers
# ----------------------------


class MockWriter(BrambleWriter):
    def __init__(self):
        # Writer API (async)
        self.add_branches = AsyncMock()
        self.close_branches = AsyncMock()
        self.append_entries = AsyncMock()
        self.update_branch_info = AsyncMock()


@pytest.fixture
def mock_writer():
    return MockWriter()


# Keep the fixture name `mock_backend` to minimize test signature churn.
# It now returns a writer, since TreeLogger no longer speaks to the backend directly.
@pytest.fixture
def mock_backend(mock_writer):
    return mock_writer


@pytest.fixture
def simple_logger(mock_writer):
    tree_logger = TreeLogger(writer=mock_writer)
    tree_logger.run = lambda *_, **__: None
    with tree_logger:
        yield tree_logger


@pytest.fixture
def log_branch(simple_logger):
    return simple_logger.root


def _get_field(obj, name, default=None):
    """Access dict keys or object attributes uniformly."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# ----------------------------
# Tests
# ----------------------------


def test_log_adds_entry_to_active_branch(mock_backend):
    captured_entries = {}

    async def capture_entries(entries):
        # entries is expected to be a dict like {branch_id: [LogEntry, ...], ...}
        captured_entries.update(entries)

    mock_backend.append_entries.side_effect = capture_entries

    with TreeLogger(writer=mock_backend) as logger:
        log("hello world", MessageType.USER, {"info": 1})

    # Ensure one branch got one log entry
    assert len(captured_entries) == 1
    [(branch_id, entries)] = list(captured_entries.items())

    assert len(entries) == 1
    entry = entries[0]
    assert entry.message == "hello world"
    assert entry.entry_metadata == {"info": 1}


def test_apply_adds_tags_and_metadata(mock_backend):
    captured_tags = {}
    captured_metadata = {}

    async def capture_branch_info(parents, children, tags, metadata):
        if tags:
            for branch_id, branch_tags in tags.items():
                captured_tags.setdefault(branch_id, set()).update(branch_tags)

        if metadata:
            for branch_id, branch_metadata in metadata.items():
                captured_metadata.setdefault(branch_id, {}).update(branch_metadata)

    mock_backend.update_branch_info.side_effect = capture_branch_info

    with TreeLogger(writer=mock_backend) as logger:
        apply(["tag1", "tag2"], {"key": "val"})

    # Validate both were applied for the same branch
    assert len(captured_tags) == 1
    assert len(captured_metadata) == 1

    branch_id = next(iter(captured_tags.keys()))
    assert branch_id in captured_metadata

    assert captured_tags[branch_id] == {"tag1", "tag2"}
    assert captured_metadata[branch_id] == {"name": "root", "key": "val"}


def test_branch_decorator_creates_new_branch(mock_backend):
    # Track entries passed to writer
    received_entries = {}

    async def capture_entries(entries):
        received_entries.update(entries)

    mock_backend.append_entries.side_effect = capture_entries

    with TreeLogger(writer=mock_backend) as logger:
        calls = []

        @branch(["sync"], {"origin": "test"})
        def test_func():
            calls.append("ran")

        test_func()

    # Now the logger has exited and flushed logs
    assert calls == ["ran"]
    assert len(received_entries) == 2


def test_async_branch_decorator_creates_new_branch(mock_backend):
    # Track entries passed to writer
    received_entries = {}

    async def capture_entries(entries):
        received_entries.update(entries)

    mock_backend.append_entries.side_effect = capture_entries

    with TreeLogger(writer=mock_backend) as logger:
        calls = []

        @branch(["async"], {"kind": "test"})
        async def test_func():
            calls.append("ran")
            return 42

        result = asyncio.run(test_func())

    assert result == 42
    assert calls == ["ran"]
    assert len(received_entries) == 2

    all_messages = [
        entry.message for entries in received_entries.values() for entry in entries
    ]
    assert any("Function call" in m for m in all_messages)
    assert any("Function return" in m for m in all_messages)


def test_branch_decorator_logs_exceptions(simple_logger):
    @branch
    def will_fail():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        will_fail()

    task = None
    while not simple_logger._tasks.empty():
        candidate = simple_logger._tasks.get_nowait()
        if (
            len(candidate) > 2
            and isinstance(candidate[2], LogEntry)
            and candidate[2].message_type == MessageType.ERROR
        ):
            task = candidate
            break
    print(task)
    assert "ValueError" in task[2].message
    assert task[2].message_type == MessageType.ERROR


def test_stringify_function_call_outputs_valid_string():
    def sample(a, b=None):
        pass

    output = _stringify_function_call(sample, [1], {"b": "test"})
    assert "sample(" in output
    assert "1" in output and "b=test" in output


@pytest.mark.parametrize("invalid", [None, 123, 3.14, [], {}])
def test_log_invalid_message_type_raises(invalid, log_branch):
    with context([log_branch]):
        with pytest.raises(ValueError):
            log("hello", message_type=invalid)


@pytest.mark.parametrize("invalid_metadata", [123, "oops", 3.14, [("key", "val")]])
def test_log_invalid_metadata_type_raises(invalid_metadata, log_branch):
    with context([log_branch]):
        with pytest.raises(ValueError):
            log("hello", entry_metadata=invalid_metadata)


def test_log_metadata_key_not_str(log_branch):
    with context([log_branch]):
        with pytest.raises(ValueError):
            log("hello", entry_metadata={42: "val"})


def test_log_metadata_value_invalid_type(log_branch):
    class Custom:
        pass

    with context([log_branch]):
        with pytest.raises(ValueError):
            log("hello", entry_metadata={"bad": Custom()})


@pytest.mark.parametrize("invalid_tags", ["notalist", 123, {"key": "value"}])
def test_apply_rejects_invalid_tags(invalid_tags, log_branch):
    with context([log_branch]):
        with pytest.raises(ValueError):
            apply(tags=invalid_tags)


@pytest.mark.parametrize("invalid_metadata", ["nope", 42, [1, 2]])
def test_apply_rejects_invalid_metadata(invalid_metadata, log_branch):
    with context([log_branch]):
        with pytest.raises(ValueError):
            apply(metadata=invalid_metadata)


@pytest.mark.parametrize("arg", ["invalid", 123, object()])
def test_apply_invalid_args(arg, log_branch):
    with context([log_branch]):
        with pytest.raises(ValueError):
            apply(arg)


def test_apply_combines_args_correctly(mock_backend):
    captured_metadata = {}
    captured_tags = {}

    async def capture_branch_info(parents, children, tags, metadata):
        print(parents, children, tags, metadata)
        if tags:
            for branch_id, branch_tags in tags.items():
                captured_tags.setdefault(branch_id, set()).update(branch_tags)

        if metadata:
            for branch_id, branch_metadata in metadata.items():
                captured_metadata.setdefault(branch_id, {}).update(branch_metadata)

    mock_backend.update_branch_info.side_effect = capture_branch_info

    with TreeLogger(writer=mock_backend) as logger:
        root = logger.root
        with context([root]):
            apply(["a", "b"], ["b", "c"], {"x": 1}, {"x": 2})

    print(root.id)
    print(captured_tags)
    print(captured_metadata)

    assert captured_tags[root.id] == {"a", "b", "c"}
    assert captured_metadata[root.id]["x"] == 2


def test_context_returns_correct_objects(log_branch):
    with context([log_branch]):
        active = context()
        assert isinstance(active, list)
        assert log_branch in active


def test_context_single_branch_is_wrapped(simple_logger):
    branch = LogBranch("test", simple_logger)
    with context(branch) as _:
        assert branch in context()


def test_context_invalid_arg_type_raises():
    with pytest.raises(ValueError):
        context("not a branch")


def test_context_list_with_invalid_element(simple_logger):
    with pytest.raises(ValueError):
        context([LogBranch("ok", simple_logger), 42])


def test_context_multiple_invalid_args(simple_logger):
    with pytest.raises(ValueError):
        context(LogBranch("one", simple_logger), "two")


def test_context_empty_list_returns_nullcontext():
    assert isinstance(context([]), nullcontext().__class__)


def test_fork_invalid_name_type_raises():
    with pytest.raises(ValueError):
        fork(123)


def test_fork_returns_nullcontext_if_no_active_branches():
    assert isinstance(fork("branchname"), nullcontext().__class__)


def test_fork_creates_new_branches_and_sets_context(simple_logger):
    with simple_logger:
        parent = simple_logger.root
        with context([parent]):
            with fork("child", tags=["forked"]) as _:
                new = context()
                assert all(b.name == "child" for b in new)
                assert all(b.parent == parent.id for b in new)
                assert all("forked" in b.tags for b in new)


def test_disable_suppresses_logging(mock_backend):
    captured_entries = {}

    async def capture_entries(entries):
        captured_entries.update(entries)

    mock_backend.append_entries.side_effect = capture_entries

    with TreeLogger(writer=mock_backend) as logger:
        with disable():
            log("this should not log")
        assert captured_entries == {}

        log("this should log")
    assert len(captured_entries) == 1


def test_enable_reactivates_logging(mock_backend):
    with TreeLogger(writer=mock_backend) as logger:
        enable()  # should be a no-op if already enabled
        log("still logs")
