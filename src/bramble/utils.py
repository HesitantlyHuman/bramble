from typing import Dict, Tuple, List, Set

import os
import uuid
import inspect
import traceback

from bramble.log_objects import MessageType


# TODO: document that setting context to 0 or below will disable the line output
def _get_location_info(
    stack_offset: int, context: int = 5
) -> Dict[str, int | str] | None:
    if context is None or context < 0:
        context = 0
    current_frame = inspect.currentframe()

    for _ in range(stack_offset):
        current_frame = current_frame.f_back
        if current_frame is None:
            return None

    info = inspect.getframeinfo(current_frame, context=context)
    location_info = {
        "file": os.path.basename(info.filename),
        "line": info.lineno,
        "function": info.function,
    }
    if context > 0:
        location_info.update({"context": "".join(info.code_context)})

    return location_info


def _generate_id(prefix: str = None) -> str:
    id_component = str(uuid.uuid4().hex)[:24]
    if prefix:
        return prefix + "-" + id_component
    return id_component


def _stringify_function_call(func, args: list, kwargs: dict):
    function_call = f"{func.__name__}("
    for arg in args:
        try:
            function_call += f"{arg},\n"
        except Exception:
            function_call += f"`ERROR`,\n"
    for key, value in kwargs.items():
        try:
            function_call += f"{key}={value},\n"
        except Exception:
            function_call += f"{key}=`ERROR`,\n"
    function_call += ")"
    return function_call


def _validate_log_call(
    message: str | Exception,
    message_type: MessageType | str = MessageType.USER,
    entry_metadata: Dict[str, str | int | float | bool] | None = None,
) -> Tuple[str, MessageType, Dict[str, str | int | float | bool] | None]:
    """Validates a bramble log call and formats objects.

    Used to ensure that we have consistent validation that happens as close to
    the user as possible.
    """
    if not isinstance(message, (str, Exception)):
        raise ValueError(
            f"`message` must be of type `str` or `Exception`, received {type(message)}."
        )

    if isinstance(message, Exception):
        message = "".join(
            traceback.TracebackException.from_exception(message).format()
        ).strip()

    if isinstance(message_type, str):
        message_type = MessageType.from_string(message_type)
    elif not isinstance(message_type, MessageType):
        raise ValueError(
            f"`message_type` must be of type `str` or `MessageType`, received {type(message_type)}."
        )

    if entry_metadata is not None and not isinstance(entry_metadata, dict):
        raise ValueError(
            f"`entry_metadata` must either be `None` or a dictionary, received {type(entry_metadata)}."
        )

    if entry_metadata is not None:
        for key, value in entry_metadata.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"Keys for `entry_metadata` must be of type `str`, received {type(key)}"
                )

            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(
                    f"Values for `entry_metadata` must be one of `str`, `int`, `float`, `bool`, received {type(value)}"
                )

    return message, message_type, entry_metadata


def _validate_tags_and_metadata(
    *args,
    tags: List[str] | Set[str] | None,
    metadata: Dict[str, str | int | float | bool] | None,
) -> Tuple[Set[str] | None, Dict[str, str | int | float | bool] | None]:
    """Validates a bramble tags and metadata for functional API.

    Used to ensure that we have consistent validation that happens as close to
    the user as possible.
    """
    if tags is not None:
        if not isinstance(tags, (list, set)):
            raise ValueError(
                f"`tags` must be of type `list` or `set`, received {type(tags)}."
            )
        args = (*args, tags)

    if metadata is not None:
        if not isinstance(metadata, dict):
            raise ValueError(
                f"`metadata` must be of type `dict`, received {type(metadata)}."
            )
        args = (*args, metadata)

    # Validate args and collect them
    collected_metadata = {}
    collected_tags = set()

    for arg in args:
        if isinstance(arg, (list, set)):
            if not all([isinstance(element, str) for element in arg]):
                raise ValueError(
                    f"Tag `list` or `set` arguments must be a list of string tags, received {arg}"
                )
            collected_tags.update(arg)
        elif isinstance(arg, dict):
            for key, value in arg.items():
                if not isinstance(key, str):
                    raise ValueError(
                        f"Metadata `dict` arguments must have string keys, received {type(key)}"
                    )
                if not isinstance(value, (str, int, float, bool)):
                    raise ValueError(
                        f"Metadata `dict` arguments must have values of type `str`, `int`, `float`, or `bool`, received {type(value)}"
                    )
            collected_metadata.update(arg)
        else:
            raise ValueError(
                f"Arguments must be of type `list`, `set` or `dict`, received {type(arg)}"
            )

    if len(collected_tags) == 0:
        collected_tags = None

    if len(collected_metadata) == 0:
        collected_metadata = None

    return collected_tags, collected_metadata
