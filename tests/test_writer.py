# test_writer.py
import asyncio
import pytest
from unittest.mock import AsyncMock

from bramble.backends.base import BrambleBackend
from bramble.writer import BrambleWriter


# ----------------------------
# Fakes / helpers
# ----------------------------


class _FakeCompressor:
    """
    Minimal stand-in for EntryCompressor / MetadataCompressor instances.

    The real compressors return bytes; we do the same, but we do NOT depend on
    LogEntry internals (keeps these tests stable across log object changes).
    """

    def __init__(self, prefix: bytes):
        self._prefix = prefix
        self.calls = []  # keep a trace for extra assertions if desired

    def add(self, branch_id: str, **kwargs) -> bytes:
        # Deterministic payload; include branch_id to make debugging easier.
        self.calls.append((branch_id, kwargs))
        return self._prefix + branch_id.encode("utf-8") + b"|"


class _FakeEntryCompressor:
    @staticmethod
    def new(*, quality: int):
        # quality is accepted but ignored in the fake
        return _FakeCompressor(prefix=b"E:")


class _FakeMetadataCompressor:
    @staticmethod
    def new(*, quality: int):
        return _FakeCompressor(prefix=b"M:")


class MockBackend(BrambleBackend):
    """
    A backend mock that captures async calls the writer is expected to make.

    We intentionally only implement the async methods BrambleWriter uses:
      - async_add_branches
      - async_assign_chunks
      - async_append_data
    """

    def __init__(self):
        self.async_add_branches = AsyncMock()
        self.async_assign_chunks = AsyncMock()
        self.async_append_data = AsyncMock()


@pytest.fixture
def mock_backend():
    return MockBackend()


@pytest.fixture
def id_gen(monkeypatch):
    """
    Make _generate_id deterministic for tests:
      ec0, ec1, ...
      mc0, mc1, ...
    """
    import bramble.writer as writer_mod

    counters = {"ec": 0, "mc": 0}

    def _fake_generate_id(prefix: str) -> str:
        i = counters[prefix]
        counters[prefix] += 1
        return f"{prefix}{i}"

    monkeypatch.setattr(writer_mod, "_generate_id", _fake_generate_id)
    return counters


@pytest.fixture
def patched_compressors(monkeypatch):
    """
    Replace EntryCompressor/MetadataCompressor factories with fakes so we don't depend on
    compression internals or LogEntry structure.
    """
    import bramble.writer as writer_mod

    monkeypatch.setattr(writer_mod, "EntryCompressor", _FakeEntryCompressor)
    monkeypatch.setattr(writer_mod, "MetadataCompressor", _FakeMetadataCompressor)


@pytest.fixture
def writer(mock_backend, id_gen, patched_compressors):
    """
    A small writer instance for assignment behavior tests.
    - 4 chunks: makes spread/affinity tests easy to reason about.
    - base_assignment_imbalance_num=1 and max_factor=1 makes imbalance trigger fast.
    """
    w = BrambleWriter(
        backend=mock_backend,
        num_simultaneous_chunks=4,
        chunk_size_mb=1.0,  # rotation tests override this
        compression_quality=6,
        max_assignment_imbalance_factor=1.0,
        base_assignment_imbalance_num=1,
    )

    return w


def _run(coro):
    # No pytest-asyncio; run coroutines directly.
    return asyncio.run(coro)


def _make_entries(branch_id: str, n: int = 1):
    """
    Return n dummy log entries. We don't need real LogEntry objects because
    compressors are patched to ignore the entry payload.
    """
    return [object() for _ in range(n)]


# ----------------------------
# Tests requested in writer TODOs
# ----------------------------


def test_incorrect_instantiation_values_give_errors(mock_backend):
    # backend must be BrambleBackend
    with pytest.raises(ValueError):
        BrambleWriter(backend="not-a-backend")  # type: ignore[arg-type]

    # max_assignment_imbalance_factor must be int/float
    with pytest.raises(ValueError):
        BrambleWriter(
            backend=mock_backend, max_assignment_imbalance_factor="nope"
        )  # type: ignore[arg-type]

    # base_assignment_imbalance_num must be int/float
    with pytest.raises(ValueError):
        BrambleWriter(
            backend=mock_backend, base_assignment_imbalance_num="nope"
        )  # type: ignore[arg-type]


def test_branches_have_entry_and_meta_compressor_after_assignment(writer):
    _run(writer.add_branches({("b1", "name")}))

    assert "b1" in writer._id_to_entry_compressor_map
    assert "b1" in writer._id_to_meta_compressor_map
    assert writer._id_to_entry_compressor_map["b1"] in writer._entry_compressors
    assert writer._id_to_meta_compressor_map["b1"] in writer._meta_compressors


def test_assigning_multiple_branches_works(writer):
    _run(writer.add_branches({("b1", "n1"), ("b2", "n2"), ("b3", "n3")}))

    assert set(writer._id_to_entry_compressor_map.keys()) == {"b1", "b2", "b3"}
    assert set(writer._id_to_meta_compressor_map.keys()) == {"b1", "b2", "b3"}


def test_same_name_prefers_same_compressors_when_possible(writer):
    _run(writer.add_branches({("b1", "same")}))
    _run(writer.add_branches({("b2", "same")}))

    # "When possible": with our imbalance settings, this should hold for the first few
    assert (
        writer._id_to_entry_compressor_map["b1"]
        == writer._id_to_entry_compressor_map["b2"]
    )
    assert (
        writer._id_to_meta_compressor_map["b1"]
        == writer._id_to_meta_compressor_map["b2"]
    )


def test_different_names_spread_across_compressors(writer):
    # With 4 compressors and min-assignment selection, different names should spread
    _run(writer.add_branches({("b1", "a"), ("b2", "b"), ("b3", "c"), ("b4", "d")}))

    entry_chunks = {
        writer._id_to_entry_compressor_map[b] for b in ["b1", "b2", "b3", "b4"]
    }
    meta_chunks = {
        writer._id_to_meta_compressor_map[b] for b in ["b1", "b2", "b3", "b4"]
    }

    # Expect at least 2 different chunks used (spread), typically 4 with these settings.
    assert len(entry_chunks) >= 2
    assert len(meta_chunks) >= 2


def test_same_name_fills_second_compressor_after_imbalance_reached(
    mock_backend, id_gen, patched_compressors
):
    """
    Force an imbalance trigger quickly.

    We use:
      - 2 simultaneous chunks
      - base_assignment_imbalance_num=0
      - max_factor=1.0
    so max_entry_allowed becomes min_assignments * 1.0, meaning:
      - once one chunk gets ahead of the minimum, name affinity should break.
    """
    w = BrambleWriter(
        backend=mock_backend,
        num_simultaneous_chunks=2,
        chunk_size_mb=1.0,
        compression_quality=6,
        max_assignment_imbalance_factor=1.0,
        base_assignment_imbalance_num=1,
    )

    # seed maps like in the writer fixture
    for chunk_id in list(w._entry_compressors.keys()):
        w._entry_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)
    for chunk_id in list(w._meta_compressors.keys()):
        w._meta_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)

    # Add 3 branches with the same name. With strict imbalance limits, we should
    # see at least two different entry chunks and two different meta chunks used.
    _run(w.add_branches({("b1", "same"), ("b2", "same"), ("b3", "same")}))

    entry_chunks = {
        w._id_to_entry_compressor_map["b1"],
        w._id_to_entry_compressor_map["b2"],
        w._id_to_entry_compressor_map["b3"],
    }
    meta_chunks = {
        w._id_to_meta_compressor_map["b1"],
        w._id_to_meta_compressor_map["b2"],
        w._id_to_meta_compressor_map["b3"],
    }

    assert len(entry_chunks) >= 2
    assert len(meta_chunks) >= 2


def test_adding_branches_adds_to_master_list_and_assigns_chunks_by_type(
    writer, mock_backend
):
    _run(writer.add_branches({("b1", "n1"), ("b2", "n2")}))

    # master list: writer passes a set of ids
    assert mock_backend.async_add_branches.await_count == 1
    try:
        added_ids = mock_backend.async_add_branches.await_args.kwargs["branch_ids"]
    except KeyError:
        added_ids = mock_backend.async_add_branches.await_args.args[0]
    assert set(added_ids) == {"b1", "b2"}

    # chunk assignments: one call for "ec" and one for "mc"
    assert mock_backend.async_assign_chunks.await_count == 2
    calls = mock_backend.async_assign_chunks.await_args_list

    types = [c.kwargs["chunk_type"] for c in calls]
    assert set(types) == {"ec", "mc"}

    # verify structure of branch_chunks payloads
    for c in calls:
        branch_chunks = c.kwargs["branch_chunks"]
        assert isinstance(branch_chunks, dict)
        assert set(branch_chunks.keys()) == {"b1", "b2"}
        assert all(isinstance(v, (set, list, tuple)) for v in branch_chunks.values())


def test_closing_branches_removes_mappings(writer):
    _run(writer.add_branches({("b1", "n"), ("b2", "n")}))
    assert "b1" in writer._id_to_entry_compressor_map
    assert "b1" in writer._id_to_meta_compressor_map

    _run(writer.close_branches({"b1"}))

    assert "b1" not in writer._id_to_entry_compressor_map
    assert "b1" not in writer._id_to_meta_compressor_map


def test_closing_branches_removes_name_if_all_branches_with_name_removed(writer):
    _run(writer.add_branches({("b1", "same"), ("b2", "same")}))

    assert "same" in writer._name_to_entry_compressor_map
    assert "same" in writer._name_to_meta_compressor_map

    _run(writer.close_branches({"b1", "b2"}))

    # After close, maps are rebuilt; "same" should not remain if no branch uses it.
    assert "same" not in writer._name_to_entry_compressor_map
    assert "same" not in writer._name_to_meta_compressor_map


def test_writing_appends_data_to_backend_chunks(writer, mock_backend):
    _run(writer.add_branches({("b1", "n1")}))

    captured = {}

    async def capture_append(chunk_data):
        # chunk_data: {chunk_id: bytes}
        captured.update(chunk_data)
        # Return updated sizes
        return {k: len(v) for k, v in chunk_data.items()}

    mock_backend.async_append_data.side_effect = capture_append

    _run(writer.append_entries({"b1": _make_entries("b1", n=3)}))

    assert mock_backend.async_append_data.await_count == 1
    assert len(captured) == 1
    [(chunk_id, payload)] = list(captured.items())
    assert chunk_id == writer._id_to_entry_compressor_map["b1"]
    assert isinstance(payload, (bytes, bytearray))
    assert payload.startswith(b"E:b1|")


def test_going_over_chunk_size_triggers_new_chunk_and_removes_old_chunk_from_mappings(
    mock_backend, id_gen, patched_compressors
):
    # Small chunk size to force rotation on first write.
    w = BrambleWriter(
        backend=mock_backend,
        num_simultaneous_chunks=2,
        chunk_size_mb=0.000001,  # ~1 byte (forces immediate rotation)
        compression_quality=6,
        max_assignment_imbalance_factor=10.0,
        base_assignment_imbalance_num=1,
    )

    for chunk_id in list(w._entry_compressors.keys()):
        w._entry_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)
    for chunk_id in list(w._meta_compressors.keys()):
        w._meta_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)

    _run(w.add_branches({("b1", "n1")}))
    old_chunk = w._id_to_entry_compressor_map["b1"]

    async def capture_append(chunk_data):
        # pretend backend sizes are cumulative; store size for each chunk_id
        return {k: len(v) for k, v in chunk_data.items()}

    mock_backend.async_append_data.side_effect = capture_append

    # Write enough that rotation condition triggers
    _run(w.append_entries({"b1": _make_entries("b1", n=1)}))

    # After rotation, mapping should move to a new chunk
    new_chunk = w._id_to_entry_compressor_map["b1"]
    assert new_chunk != old_chunk

    # Old chunk should have been cleaned up from compressor/mapping sets
    assert old_chunk not in w._entry_compressors
    assert old_chunk not in w._entry_chunk_to_ids_and_names
    assert old_chunk not in w._chunk_sizes


def test_new_chunk_has_ids_and_names_of_old_chunk(
    mock_backend, id_gen, patched_compressors
):
    w = BrambleWriter(
        backend=mock_backend,
        num_simultaneous_chunks=2,
        chunk_size_mb=0.000001,  # force rotation
        compression_quality=6,
        max_assignment_imbalance_factor=10.0,
        base_assignment_imbalance_num=1,
    )

    for chunk_id in list(w._entry_compressors.keys()):
        w._entry_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)
    for chunk_id in list(w._meta_compressors.keys()):
        w._meta_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)

    _run(w.add_branches({("b1", "name")}))
    old_chunk = w._id_to_entry_compressor_map["b1"]
    old_ids_and_names = set(w._entry_chunk_to_ids_and_names[old_chunk])

    async def capture_append(chunk_data):
        return {k: len(v) for k, v in chunk_data.items()}

    mock_backend.async_append_data.side_effect = capture_append

    _run(w.append_entries({"b1": _make_entries("b1", n=1)}))

    new_chunk = w._id_to_entry_compressor_map["b1"]
    assert set(w._entry_chunk_to_ids_and_names[new_chunk]) == old_ids_and_names


def test_creating_new_chunk_keeps_constant_number_of_compressors(
    mock_backend, id_gen, patched_compressors
):
    w = BrambleWriter(
        backend=mock_backend,
        num_simultaneous_chunks=3,
        chunk_size_mb=0.000001,  # force rotation
        compression_quality=6,
        max_assignment_imbalance_factor=10.0,
        base_assignment_imbalance_num=1,
    )

    for chunk_id in list(w._entry_compressors.keys()):
        w._entry_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)
    for chunk_id in list(w._meta_compressors.keys()):
        w._meta_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)

    _run(w.add_branches({("b1", "n1")}))

    async def capture_append(chunk_data):
        return {k: len(v) for k, v in chunk_data.items()}

    mock_backend.async_append_data.side_effect = capture_append

    before = len(w._entry_compressors)
    _run(w.append_entries({"b1": _make_entries("b1", n=1)}))
    after = len(w._entry_compressors)

    assert before == w.num_simultaneous_chunks
    assert after == w.num_simultaneous_chunks


def test_append_entries_works(writer, mock_backend):
    _run(writer.add_branches({("b1", "n1"), ("b2", "n2")}))

    captured = {}

    async def capture_append(chunk_data):
        captured.update(chunk_data)
        return {k: len(v) for k, v in chunk_data.items()}

    mock_backend.async_append_data.side_effect = capture_append

    _run(
        writer.append_entries(
            {"b1": _make_entries("b1", 2), "b2": _make_entries("b2", 1)}
        )
    )

    # should write to (up to) two chunks (may coincide depending on assignment)
    assert mock_backend.async_append_data.await_count == 1
    assert isinstance(captured, dict)
    assert all(isinstance(v, (bytes, bytearray)) for v in captured.values())


def test_update_branch_info_works(writer, mock_backend):
    _run(writer.add_branches({("b1", "n1"), ("b2", "n2")}))

    captured = {}

    async def capture_append(chunk_data):
        captured.update(chunk_data)
        return {k: len(v) for k, v in chunk_data.items()}

    mock_backend.async_append_data.side_effect = capture_append

    _run(
        writer.update_branch_info(
            parents={"b1": "p"},
            children={"b1": {"c1", "c2"}, "b2": {"c3"}},
            tags={"b1": {"t1"}, "b2": {"t2", "t3"}},
            metadata={"b1": {"x": 1}, "b2": {"y": True}},
        )
    )

    assert mock_backend.async_append_data.await_count == 1
    assert len(captured) >= 1
    # Metadata compressor prefix should appear in payloads
    assert any(payload.startswith(b"M:") for payload in captured.values())


# ----------------------------
# Additional coverage tests (helpful / defensive)
# ----------------------------


def test_close_branches_noop_when_unknown_ids(writer):
    # Closing an unknown branch should not crash and should not rebuild maps
    # in a way that breaks future operation.
    _run(writer.close_branches({"does-not-exist"}))


def test_add_branches_calls_backend_once_per_kind(
    mock_backend, id_gen, patched_compressors
):
    w = BrambleWriter(
        backend=mock_backend,
        num_simultaneous_chunks=2,
        chunk_size_mb=1.0,
        compression_quality=6,
        max_assignment_imbalance_factor=10.0,
        base_assignment_imbalance_num=1,
    )
    for chunk_id in list(w._entry_compressors.keys()):
        w._entry_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)
    for chunk_id in list(w._meta_compressors.keys()):
        w._meta_chunk_to_ids_and_names.setdefault(chunk_id, set())
        w._chunk_sizes.setdefault(chunk_id, 0)

    _run(w.add_branches({("b1", "n1")}))
    assert mock_backend.async_add_branches.await_count == 1
    assert mock_backend.async_assign_chunks.await_count == 2


def _assert_old_chunk_fully_purged_from_entry_mappings(
    w: BrambleWriter, old_chunk: str
):
    # compressors / chunk tables
    assert old_chunk not in w._entry_compressors
    assert old_chunk not in w._entry_chunk_to_ids_and_names

    # assignment options should not reference a deleted chunk
    assert old_chunk not in w._entry_chunk_assignment_options

    # name affinity should not reference a deleted chunk
    for name, chunk_ids in w._name_to_entry_compressor_map.items():
        assert (
            old_chunk not in chunk_ids
        ), f"old entry chunk leaked into name map for {name}"

    # id->chunk mapping should not reference deleted chunk
    for bid, chunk_id in w._id_to_entry_compressor_map.items():
        assert chunk_id != old_chunk, f"branch {bid} still points to old entry chunk"


def _assert_new_chunk_present_in_entry_mappings(
    w: BrambleWriter, new_chunk: str, expected_ids_and_names
):
    assert new_chunk in w._entry_compressors
    assert new_chunk in w._entry_chunk_to_ids_and_names
    assert w._entry_chunk_to_ids_and_names[new_chunk] == expected_ids_and_names

    # id->chunk mapping should point to new chunk for all transferred branches
    for bid, _name in expected_ids_and_names:
        assert w._id_to_entry_compressor_map[bid] == new_chunk

    # name affinity should include new chunk for each name
    for _bid, name in expected_ids_and_names:
        assert new_chunk in w._name_to_entry_compressor_map.get(
            name, set()
        ), f"new entry chunk missing from name map for {name}"


def _assert_old_chunk_fully_purged_from_meta_mappings(w: BrambleWriter, old_chunk: str):
    assert old_chunk not in w._meta_compressors
    assert old_chunk not in w._meta_chunk_to_ids_and_names
    assert old_chunk not in w._meta_chunk_assignment_options

    for name, chunk_ids in w._name_to_meta_compressor_map.items():
        assert (
            old_chunk not in chunk_ids
        ), f"old meta chunk leaked into name map for {name}"

    for bid, chunk_id in w._id_to_meta_compressor_map.items():
        assert chunk_id != old_chunk, f"branch {bid} still points to old meta chunk"


def _assert_new_chunk_present_in_meta_mappings(
    w: BrambleWriter, new_chunk: str, expected_ids_and_names
):
    assert new_chunk in w._meta_compressors
    assert new_chunk in w._meta_chunk_to_ids_and_names
    assert w._meta_chunk_to_ids_and_names[new_chunk] == expected_ids_and_names

    for bid, _name in expected_ids_and_names:
        assert w._id_to_meta_compressor_map[bid] == new_chunk

    for _bid, name in expected_ids_and_names:
        assert new_chunk in w._name_to_meta_compressor_map.get(
            name, set()
        ), f"new meta chunk missing from name map for {name}"


def test_rotation_purges_old_entry_chunk_from_all_mappings_and_adds_new_one(
    mock_backend, id_gen, patched_compressors
):
    """
    Verifies: after entry rotation, the old entry chunk id is not present in:
      - _entry_compressors
      - _entry_chunk_to_ids_and_names
      - _entry_chunk_assignment_options
      - _name_to_entry_compressor_map values
      - any _id_to_entry_compressor_map value

    And that the new chunk is present in the expected places and carries the
    transferred (branch_id, name) set.
    """
    w = BrambleWriter(
        backend=mock_backend,
        num_simultaneous_chunks=2,
        chunk_size_mb=0.000001,  # force rotation fast
        compression_quality=6,
        max_assignment_imbalance_factor=10.0,
        base_assignment_imbalance_num=1,
    )

    # Assign one branch, then write to force entry rotation.
    _run(w.add_branches({("b1", "name")}))

    old_entry_chunk = w._id_to_entry_compressor_map["b1"]
    expected_ids_and_names = set(w._entry_chunk_to_ids_and_names[old_entry_chunk])

    async def capture_append(chunk_data):
        # backend returns total sizes
        return {k: len(v) for k, v in chunk_data.items()}

    mock_backend.async_append_data.side_effect = capture_append

    _run(w.append_entries({"b1": _make_entries("b1", n=1)}))

    new_entry_chunk = w._id_to_entry_compressor_map["b1"]
    assert new_entry_chunk != old_entry_chunk

    _assert_old_chunk_fully_purged_from_entry_mappings(w, old_entry_chunk)
    _assert_new_chunk_present_in_entry_mappings(
        w, new_entry_chunk, expected_ids_and_names
    )


def test_rotation_purges_old_meta_chunk_from_all_mappings_and_adds_new_one(
    mock_backend, id_gen, patched_compressors
):
    """
    Same as entry rotation test, but for metadata rotation via update_branch_info.
    """
    w = BrambleWriter(
        backend=mock_backend,
        num_simultaneous_chunks=2,
        chunk_size_mb=0.000001,  # force rotation fast
        compression_quality=6,
        max_assignment_imbalance_factor=10.0,
        base_assignment_imbalance_num=1,
    )

    _run(w.add_branches({("b1", "name")}))

    old_meta_chunk = w._id_to_meta_compressor_map["b1"]
    expected_ids_and_names = set(w._meta_chunk_to_ids_and_names[old_meta_chunk])

    async def capture_append(chunk_data):
        return {k: len(v) for k, v in chunk_data.items()}

    mock_backend.async_append_data.side_effect = capture_append

    _run(
        w.update_branch_info(
            parents={"b1": "p"},
            children={"b1": {"c1"}},
            tags={"b1": {"t"}},
            metadata={"b1": {"x": 1}},
        )
    )

    new_meta_chunk = w._id_to_meta_compressor_map["b1"]
    assert new_meta_chunk != old_meta_chunk

    _assert_old_chunk_fully_purged_from_meta_mappings(w, old_meta_chunk)
    _assert_new_chunk_present_in_meta_mappings(
        w, new_meta_chunk, expected_ids_and_names
    )
