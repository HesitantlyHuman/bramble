from typing import Dict, List

import inspect

from treelog.context import _CURRENT_BRANCH_IDS, _LIVE_BRANCHES
from treelog.utils import stringify_function_call
from treelog.logs import MessageType


def _async_branch(func, name, tags=None, metadata=None):
    async def wrapper(*args, **kwargs):
        current_logger_ids = _CURRENT_BRANCH_IDS.get()

        if len(current_logger_ids) == 0:
            return await func(*args, **kwargs)

        new_logger_ids = set()
        for logger_id in current_logger_ids:
            old_logger = _LIVE_BRANCHES[logger_id]
            new_logger = old_logger.branch(name=name)

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


def _sync_branch(func, name, tags=None, metadata=None):
    def wrapper(*args, **kwargs):
        current_logger_ids = _CURRENT_BRANCH_IDS.get()

        if len(current_logger_ids) == 0:
            return func(*args, **kwargs)

        new_logger_ids = set()
        for logger_id in current_logger_ids:
            old_logger = _LIVE_BRANCHES[logger_id]
            new_logger = old_logger.branch(name=name)

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
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            log(e, MessageType.ERROR)
            raise e

    return wrapper


def _sync_tree_log_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log(e, MessageType.ERROR)
            raise e

    return wrapper


def _async_tree_log_args(func):
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
):
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
                    f"Keys for `metadata` must be of type `str`, recieved {type(key)}"
                )
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(
                    f"Values for `metadata` must be one of `str`, `int`, `float`, `bool`, recieved {type(value)}"
                )

    def _branch(func):
        if inspect.iscoroutinefunction(func):
            return _async_tree_log_exceptions(
                _async_branch(
                    _async_tree_log_args(func),
                    func.__name__,
                    tags=tags,
                    metadata=metadata,
                )
            )
        else:
            return _sync_tree_log_exceptions(
                _sync_branch(
                    _sync_tree_log_args(func),
                    func.__name__,
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
    current_branch_ids = _CURRENT_BRANCH_IDS.get()
    if current_branch_ids is None:
        return

    for branch_id in current_branch_ids:
        branch = _LIVE_BRANCHES[branch_id]
        branch.log(
            message=message, message_type=message_type, entry_metadata=entry_metadata
        )
