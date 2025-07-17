import pytest
from bramble.utils import (
    _validate_log_call,
    _validate_tags_and_metadata,
    _stringify_function_call,
)
from bramble.logs import MessageType


def test_validate_log_call_str_message_and_default_type():
    msg, msg_type, meta = _validate_log_call("hello")
    assert msg == "hello"
    assert msg_type == MessageType.USER
    assert meta is None


def test_validate_log_call_exception_message():
    try:
        raise ValueError("broken")
    except Exception as e:
        msg, msg_type, meta = _validate_log_call(e)
        assert "ValueError: broken" in msg
        assert msg_type == MessageType.USER
        assert meta is None


def test_validate_log_call_with_string_message_type():
    msg, msg_type, meta = _validate_log_call("info", "error")
    assert msg == "info"
    assert msg_type == MessageType.ERROR


def test_validate_log_call_invalid_message_type_raises():
    with pytest.raises(ValueError):
        _validate_log_call("msg", object())


def test_validate_log_call_invalid_metadata_type_raises():
    with pytest.raises(ValueError):
        _validate_log_call("msg", entry_metadata="not a dict")


def test_validate_log_call_metadata_invalid_key_type():
    with pytest.raises(ValueError):
        _validate_log_call("msg", entry_metadata={1: "val"})


def test_validate_log_call_metadata_invalid_value_type():
    with pytest.raises(ValueError):
        _validate_log_call("msg", entry_metadata={"key": object()})


def test_validate_tags_and_metadata_valid_combination():
    tags, metadata = _validate_tags_and_metadata(
        ["a", "b"], {"x": 1}, tags=["c"], metadata={"y": 2}
    )
    assert set(tags) == {"a", "b", "c"}
    assert metadata == {"x": 1, "y": 2}


def test_validate_tags_and_metadata_empty_returns_none():
    tags, metadata = _validate_tags_and_metadata([], {}, tags=None, metadata=None)
    assert tags is None
    assert metadata is None


def test_validate_tags_and_metadata_invalid_tag_list():
    with pytest.raises(ValueError):
        _validate_tags_and_metadata([123], tags=None, metadata=None)


def test_validate_tags_and_metadata_invalid_metadata_key():
    with pytest.raises(ValueError):
        _validate_tags_and_metadata({1: "val"}, tags=None, metadata=None)


def test_validate_tags_and_metadata_invalid_metadata_value():
    with pytest.raises(ValueError):
        _validate_tags_and_metadata({"key": object()}, tags=None, metadata=None)


def test_validate_tags_and_metadata_invalid_arg_type():
    with pytest.raises(ValueError):
        _validate_tags_and_metadata("not a list or dict", tags=None, metadata=None)


def test_validate_tags_and_metadata_multi_args():
    tags, metadata = _validate_tags_and_metadata(
        ["a", "b", "c"],
        ["d", "e", "f"],
        {"1": 1},
        ["g"],
        {"2": 1},
        {"2": 2, "3": 3},
        tags=None,
        metadata=None,
    )
    assert set(tags) == set(["a", "b", "c", "d", "e", "f", "g"])
    assert metadata == {"1": 1, "2": 2, "3": 3}


def test_stringify_function_call_handles_args_and_kwargs():
    def dummy(a, b=2):
        pass

    s = _stringify_function_call(dummy, [1], {"b": 2})
    assert "dummy(" in s
    assert "1" in s
    assert "b=2" in s


def test_stringify_function_call_handles_unprintable():
    def dummy():
        pass

    class Unprintable:
        def __str__(self):
            raise Exception()

    s = _stringify_function_call(dummy, [Unprintable()], {"x": Unprintable()})
    assert "`ERROR`" in s
