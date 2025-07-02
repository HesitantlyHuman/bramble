from typing import Dict, List, Callable, Any, Awaitable

import functools
import inspect

from treelog.utils import stringify_function_call, validate_log_call
from treelog.context import _CURRENT_BRANCH_IDS, _LIVE_BRANCHES
from treelog.logs import MessageType

# TODO: improve the exception trace results when the error does not originate in
# treelog.functional. We currently end up with 4 wrappers in the trace. Either
# we can flatten the wrapper to just one (nice, bc it is still clear that we are
# in fact wrapping the function), or clean up the traceback manually. (Less a
# fan but more powerful, since idk how hard cleaning up the wrapper will be)


def _async_branch(func, tags=None, metadata=None):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        current_logger_ids = _CURRENT_BRANCH_IDS.get()

        if len(current_logger_ids) == 0:
            return await func(*args, **kwargs)

        new_logger_ids = set()
        for logger_id in current_logger_ids:
            old_logger = _LIVE_BRANCHES[logger_id]
            new_logger = old_logger.branch(name=func.__name__)

            if tags is not None:
                new_logger.add_tags(tags)

            if metadata is not None:
                new_logger.add_metadata(metadata)

            _LIVE_BRANCHES[new_logger.id] = new_logger
            new_logger_ids.add(new_logger.id)
        _CURRENT_BRANCH_IDS.set(new_logger_ids)

        output = await func(*args, **kwargs)

        _CURRENT_BRANCH_IDS.set(current_logger_ids)

        return output

    return wrapper


def _sync_branch(func, tags=None, metadata=None):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        current_logger_ids = _CURRENT_BRANCH_IDS.get()

        if len(current_logger_ids) == 0:
            return func(*args, **kwargs)

        new_logger_ids = set()
        for logger_id in current_logger_ids:
            old_logger = _LIVE_BRANCHES[logger_id]
            new_logger = old_logger.branch(name=func.__name__)

            if tags is not None:
                new_logger.add_tags(tags)

            if metadata is not None:
                new_logger.add_metadata(metadata)

            _LIVE_BRANCHES[new_logger.id] = new_logger
            new_logger_ids.add(new_logger.id)
        _CURRENT_BRANCH_IDS.set(new_logger_ids)

        output = func(*args, **kwargs)

        _CURRENT_BRANCH_IDS.set(current_logger_ids)

        return output

    return wrapper


def _async_tree_log_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            log(e, MessageType.ERROR)
            raise e

    return wrapper


def _sync_tree_log_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log(e, MessageType.ERROR)
            raise e

    return wrapper


def _async_tree_log_args(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        log(
            "Function call:\n" + stringify_function_call(func, args, kwargs),
            MessageType.SYSTEM,
        )

        output = await func(*args, **kwargs)

        try:
            return_string = f"Function return:\n{output}"
        except Exception:
            return_string = "Function return:\n`ERROR`"
        log(return_string, MessageType.SYSTEM)

        return output

    return wrapper


def _sync_tree_log_args(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        log(
            "Function call:\n" + stringify_function_call(func, args, kwargs),
            MessageType.SYSTEM,
        )

        output = func(*args, **kwargs)

        try:
            return_string = f"Function return:\n{output}"
        except Exception:
            return_string = "Function return:\n`ERROR`"
        log(return_string, MessageType.SYSTEM)

        return output

    return wrapper


def branch(
    _func=None,
    *,
    tags: List[str] | None = None,
    metadata: Dict[str, str | int | float | bool] | None = None,
) -> Callable[..., Any | Awaitable[Any]]:
    """Mark a function for branching.

    Using this decorator will mark a function for logging to branch anytime
    execution enters. Any treelog branches currently in context will create a
    new child, using their `branch` method. Logging that happens in this
    function will be added to the child branches.

    IMPORTANT: `branch` will not do anything if there are no treelog branches in
    the current context. You must use the TreeLogger context manager pattern if
    you wish `branch` to do anything.

    Args:
        tags (List[str], optional): An optional list of tags to add to each
            branch for this function.
        metadata: (Dict[str, str | int | float | bool], optional): An optional
            list of metadata to add to each branch for this function.
    """
    if tags is not None and not isinstance(tags, list):
        raise ValueError(f"`tags` must be of type `list`, received {type(tags)}.")
    if tags is not None and not all([isinstance(tag, str) for tag in tags]):
        raise ValueError("`tags` must all be of type `str`.")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError(
            f"`metadata` must be of type `dict`, received {type(metadata)}."
        )
    if metadata is not None:
        for key, value in metadata.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"Keys for `metadata` must be of type `str`, received {type(key)}"
                )
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(
                    f"Values for `metadata` must be one of `str`, `int`, `float`, `bool`, received {type(value)}"
                )

    @functools.wraps(_func)
    def _branch(func):
        if inspect.iscoroutinefunction(func):
            return _async_tree_log_exceptions(
                _async_branch(
                    _async_tree_log_args(func),
                    tags=tags,
                    metadata=metadata,
                )
            )
        else:
            return _sync_tree_log_exceptions(
                _sync_branch(
                    _sync_tree_log_args(func),
                    tags=tags,
                    metadata=metadata,
                )
            )

    if _func is None:
        return _branch
    else:
        return _branch(func=_func)


def log(
    message: str,
    message_type: MessageType | str = MessageType.USER,
    entry_metadata: Dict[str, str | int | float | bool] | None = None,
):
    """Log a message to the active `treelog` branches.

    Will log a message to any treelog branches currently in context. Each branch
    will receive an identical log entry.

    IMPORTANT: `log` will not do anything if there are no treelog branches in
    the current context. You must use the TreeLogger context manager pattern if
    you wish `log` to do anything.

    Args:
        message (str): The message to log.
        message_type (MessageType | str, optional): The type of the message.
            Defaults to MessageType.USER. Generally, MessageType.SYSTEM is used
            for system messages internal to the logging system. If a string is
            passed, an attempt is made to cast it to MessageType.
        entry_metadata (Dict[str, Union[str, int, float, bool]], optional):
            Metadata to include with the log entry. Defaults to None.

    Raises:
        ValueError: If `message` is not a string, `message_type` cannot be
        converted to a MessageType, `entry_metadata` is not a dictionary or is
        not None, the keys of `entry_metadata` are not strings, or the values of
        `entry_metadata` are not `str`, `int`, `float`, or `bool`.
    """
    # Ensure that we provide proper errors to the user's logging calls, even if
    # there are currently no loggers in context.
    message, message_type, entry_metadata = validate_log_call(
        message=message,
        message_type=message_type,
        entry_metadata=entry_metadata,
    )

    current_branch_ids = _CURRENT_BRANCH_IDS.get()
    if current_branch_ids is None:
        return

    for branch_id in current_branch_ids:
        branch = _LIVE_BRANCHES[branch_id]
        branch.log(
            message=message,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )
