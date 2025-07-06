import asyncio
import pytest

from unittest.mock import AsyncMock

from bramble.functional import log, apply, branch, stringify_function_call
from bramble.backend import BrambleWriter
from bramble.logger import TreeLogger
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


@pytest.fixture
def simple_logger(mock_backend):
    with TreeLogger(logging_backend=mock_backend) as logger:
        yield logger


@pytest.fixture
def log_branch(simple_logger):
    return simple_logger.root


def test_log_adds_entry_to_active_branch(mock_backend):
    captured_entries = {}

    async def capture_entries(entries):
        captured_entries.update(entries)

    mock_backend.async_append_entries.side_effect = capture_entries

    with TreeLogger(logging_backend=mock_backend) as logger:
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

    async def capture_tags(tags):
        captured_tags.update(tags)

    async def capture_metadata(metadata):
        captured_metadata.update(metadata)

    mock_backend.async_add_tags.side_effect = capture_tags
    mock_backend.async_update_branch_metadata.side_effect = capture_metadata

    with TreeLogger(logging_backend=mock_backend) as logger:
        apply(["tag1", "tag2"], {"key": "val"})

    # Validate both were called for the same branch
    assert len(captured_tags) == 1
    assert len(captured_metadata) == 1

    branch_id = next(iter(captured_tags.keys()))
    assert branch_id in captured_metadata

    assert set(captured_tags[branch_id]) == {"tag1", "tag2"}
    assert captured_metadata[branch_id] == {"name": "entry", "key": "val"}


def test_branch_decorator_creates_new_branch(mock_backend):
    # Track entries passed to backend
    received_entries = {}

    async def capture_entries(entries):
        received_entries.update(entries)

    mock_backend.async_append_entries.side_effect = capture_entries

    with TreeLogger(logging_backend=mock_backend) as logger:
        calls = []

        @branch(["sync"], {"origin": "test"})
        def test_func():
            calls.append("ran")

        test_func()

    # Now the logger has exited and flushed logs
    assert calls == ["ran"]
    assert len(received_entries) == 2


def test_async_branch_decorator_creates_new_branch(mock_backend):
    # Track entries passed to backend
    received_entries = {}

    async def capture_entries(entries):
        received_entries.update(entries)

    mock_backend.async_append_entries.side_effect = capture_entries

    with TreeLogger(logging_backend=mock_backend) as logger:
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

    task = simple_logger._tasks.get_nowait()
    assert "ValueError" in task[2].message
    assert task[2].message_type == MessageType.ERROR


def test_stringify_function_call_outputs_valid_string():
    def sample(a, b=None):
        pass

    output = stringify_function_call(sample, [1], {"b": "test"})
    assert "sample(" in output
    assert "1" in output and "b=test" in output
