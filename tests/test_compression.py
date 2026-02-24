# test_compression.py
import io
import pytest

from bramble.log_objects import LogEntry, MessageType
from bramble.compression import (
    PREFIX_SIZE,
    EntryCompressor,
    EntryDecompressor,
    MetadataCompressor,
    MetadataDecompressor,
)


# ----------------------------
# Helpers
# ----------------------------


def _make_entry(
    message: str,
    ts: float = 123.456,
    mt: MessageType = MessageType.USER,
    md=None,
) -> LogEntry:
    if md is None:
        md = {}
    return LogEntry(message=message, timestamp=ts, message_type=mt, entry_metadata=md)


def _concat(*parts: bytes) -> bytes:
    out = b""
    for p in parts:
        out += p
    return out


def _as_stream(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)


# ----------------------------
# "Verify that compression works" (basic smoke tests)
# ----------------------------


def test_entry_compressor_produces_bytes():
    c = EntryCompressor.new(quality=6)
    b = c.add("b1", _make_entry("hello", mt=MessageType.USER, md={"k": 1}))
    assert isinstance(b, (bytes, bytearray))
    assert len(b) > 0


def test_metadata_compressor_produces_bytes():
    c = MetadataCompressor.new(quality=6)
    b = c.add(
        "b1",
        parent="p",
        children=["c1", "c2"],
        tags=["t1", "t2"],
        metadata={"x": 1, "ok": True},
    )
    assert isinstance(b, (bytes, bytearray))
    assert len(b) > 0


# ----------------------------
# Round-trip tests (compress -> decompress -> same object)
# ----------------------------


def test_entry_round_trip_single_item_exact():
    comp = EntryCompressor.new(quality=6)
    entry = _make_entry("hello", ts=1.25, mt=MessageType.ERROR, md={"a": 1, "b": True})
    data = comp.add("branchA", entry)

    dec = EntryDecompressor.new(_as_stream(data))
    out = list(dec.read())

    assert len(out) == 1
    branch_id, out_entry = out[0]
    assert branch_id == "branchA"
    assert out_entry.message == entry.message
    assert out_entry.timestamp == entry.timestamp
    assert out_entry.message_type == entry.message_type
    assert out_entry.entry_metadata == entry.entry_metadata


def test_metadata_round_trip_single_item_exact():
    comp = MetadataCompressor.new(quality=6)
    data = comp.add(
        "branchA",
        parent="parent1",
        children=["c1", "c2", "c2"],  # duplicates should be fine
        tags=["t1", "t1", "t2"],
        metadata={"x": 1, "y": 2.5, "ok": True},
    )

    dec = MetadataDecompressor.new(_as_stream(data))
    out = list(dec.read())

    assert len(out) == 1
    branch_id, parent, children, tags, metadata = out[0]

    assert branch_id == "branchA"
    assert parent == "parent1"
    assert set(children) == {"c1", "c2"}
    assert set(tags) == {"t1", "t2"}
    assert metadata == {"x": 1, "y": 2.5, "ok": True}


# ----------------------------
# Quality sweep (0-11)
# ----------------------------


@pytest.mark.parametrize("quality", list(range(0, 12)))
def test_entry_round_trip_all_qualities(quality: int):
    comp = EntryCompressor.new(quality=quality)
    entries = [
        ("b1", _make_entry("m1", ts=1.0, mt=MessageType.SYSTEM, md={"k": 1})),
        ("b1", _make_entry("m2", ts=2.0, mt=MessageType.USER, md={"k": 2})),
        ("b2", _make_entry("m3", ts=3.0, mt=MessageType.ERROR, md={"err": "x"})),
    ]
    data = b"".join(comp.add(bid, e) for bid, e in entries)

    dec = EntryDecompressor.new(_as_stream(data))
    out = list(dec.read())

    assert len(out) == len(entries)
    for (exp_bid, exp_e), (got_bid, got_e) in zip(entries, out):
        assert got_bid == exp_bid
        assert got_e.message == exp_e.message
        assert got_e.timestamp == exp_e.timestamp
        assert got_e.message_type == exp_e.message_type
        assert got_e.entry_metadata == exp_e.entry_metadata


@pytest.mark.parametrize("quality", list(range(0, 12)))
def test_metadata_round_trip_all_qualities(quality: int):
    comp = MetadataCompressor.new(quality=quality)

    # Build a stream with multiple updates and branch switches.
    data = _concat(
        comp.add("b1", parent="p1"),
        comp.add("b1", children=["c1", "c2"]),
        comp.add("b1", tags=["t1"]),
        comp.add("b2", parent="p2", tags=["t2", "t3"], metadata={"x": 1}),
        comp.add("b2", children=["c3"], metadata={"y": False}),
    )

    dec = MetadataDecompressor.new(_as_stream(data))
    out = list(dec.read())

    # Decompressor emits one record per "branch segment" in the stream:
    # - record for b1 when we see next branch id (b2)
    # - record for b2 at end-of-stream
    assert len(out) == 2

    b1_id, b1_parent, b1_children, b1_tags, b1_meta = out[0]
    assert b1_id == "b1"
    assert b1_parent == "p1"
    assert set(b1_children) == {"c1", "c2"}
    assert set(b1_tags) == {"t1"}
    assert b1_meta == {}

    b2_id, b2_parent, b2_children, b2_tags, b2_meta = out[1]
    assert b2_id == "b2"
    assert b2_parent == "p2"
    assert set(b2_children) == {"c3"}
    assert set(b2_tags) == {"t2", "t3"}
    assert b2_meta == {"x": 1, "y": False}


# ----------------------------
# Bytestream support
# ----------------------------


def test_entry_decompression_accepts_bytestream_object():
    comp = EntryCompressor.new(quality=6)
    data = _concat(
        comp.add("b1", _make_entry("a", ts=1.0, mt=MessageType.USER)),
        comp.add("b1", _make_entry("b", ts=2.0, mt=MessageType.USER)),
    )

    stream = io.BytesIO(data)  # satisfies ByteSource via .read()
    dec = EntryDecompressor.new(stream)
    out = list(dec.read())

    assert [bid for bid, _ in out] == ["b1", "b1"]
    assert [e.message for _, e in out] == ["a", "b"]


def test_metadata_decompression_accepts_bytestream_object():
    comp = MetadataCompressor.new(quality=6)
    data = _concat(
        comp.add("b1", tags=["t1"]),
        comp.add("b1", metadata={"x": 1}),
    )

    stream = io.BytesIO(data)
    dec = MetadataDecompressor.new(stream)
    out = list(dec.read())

    assert len(out) == 1
    bid, parent, children, tags, meta = out[0]
    assert bid == "b1"
    assert parent is None
    assert set(children) == set()  # empty
    assert set(tags) == {"t1"}
    assert meta == {"x": 1}


# ----------------------------
# Different combinations of branch ids
# ----------------------------


def test_entry_branch_id_switching_is_decoded_correctly():
    comp = EntryCompressor.new(quality=6)

    expected = [
        ("b1", _make_entry("m1", ts=1.0, mt=MessageType.USER)),
        ("b1", _make_entry("m2", ts=2.0, mt=MessageType.ERROR, md={"e": 1})),
        ("b2", _make_entry("m3", ts=3.0, mt=MessageType.SYSTEM)),
        ("b1", _make_entry("m4", ts=4.0, mt=MessageType.USER, md={"x": True})),
    ]

    data = b"".join(comp.add(bid, e) for bid, e in expected)
    out = list(EntryDecompressor.new(_as_stream(data)).read())

    assert len(out) == len(expected)
    assert [bid for bid, _ in out] == [bid for bid, _ in expected]
    assert [e.message for _, e in out] == [e.message for _, e in expected]


def test_metadata_branch_id_switching_groups_updates_per_segment():
    comp = MetadataCompressor.new(quality=6)

    # b1 gets multiple updates, then b2, then b1 again
    data = _concat(
        comp.add("b1", parent="p1"),
        comp.add("b1", tags=["t1"]),
        comp.add("b2", parent="p2", children=["c1"]),
        comp.add("b1", metadata={"x": 1}),  # new segment for b1
    )

    out = list(MetadataDecompressor.new(_as_stream(data)).read())
    assert len(out) == 3

    # Segment 1: b1 until we see b2
    b1a_id, b1a_parent, b1a_children, b1a_tags, b1a_meta = out[0]
    assert b1a_id == "b1"
    assert b1a_parent == "p1"
    assert set(b1a_children) == set()
    assert set(b1a_tags) == {"t1"}
    assert b1a_meta == {}

    # Segment 2: b2 until we see b1
    b2_id, b2_parent, b2_children, b2_tags, b2_meta = out[1]
    assert b2_id == "b2"
    assert b2_parent == "p2"
    assert set(b2_children) == {"c1"}
    assert set(b2_tags) == set()
    assert b2_meta == {}

    # Segment 3: b1 at end-of-stream
    b1b_id, b1b_parent, b1b_children, b1b_tags, b1b_meta = out[2]
    assert b1b_id == "b1"
    assert b1b_parent is None
    assert set(b1b_children) == set()
    assert set(b1b_tags) == set()
    assert b1b_meta == {"x": 1}


# ----------------------------
# Additional defensive tests (EOF / truncation)
# ----------------------------


def test_entry_decompressor_raises_eof_on_truncated_stream():
    comp = EntryCompressor.new(quality=6)
    data = comp.add("b1", _make_entry("hello", ts=1.0, mt=MessageType.USER))
    truncated = data[:-1]  # drop final byte

    dec = EntryDecompressor.new(_as_stream(truncated))
    with pytest.raises(EOFError):
        list(dec.read())


def test_metadata_decompressor_raises_eof_on_truncated_stream():
    comp = MetadataCompressor.new(quality=6)
    data = comp.add("b1", tags=["t1", "t2"])
    truncated = data[:-1]

    dec = MetadataDecompressor.new(_as_stream(truncated))
    with pytest.raises(EOFError):
        list(dec.read())


def test_entry_decompressor_returns_none_on_empty_stream():
    dec = EntryDecompressor.new(_as_stream(b""))
    assert dec.read_next() is None


def test_metadata_decompressor_returns_none_on_empty_stream():
    dec = MetadataDecompressor.new(_as_stream(b""))
    assert dec.read_next() is None


def test_entry_prefix_size_constant_is_two_bytes():
    # small sanity check to prevent accidental protocol drift
    assert PREFIX_SIZE == 2
