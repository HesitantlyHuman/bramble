from typing import Dict, Tuple

import traceback

from bramble.logs import MessageType


def stringify_function_call(func, args: list, kwargs: dict):
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


def validate_log_call(
    message: str | Exception,
    message_type: MessageType | str = MessageType.USER,
    entry_metadata: Dict[str, str | int | float | bool] | None = None,
) -> Tuple[str, MessageType, Dict[str, str | int | float | bool] | None]:
    """Validates a lumberjack log call and formats objects.

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
