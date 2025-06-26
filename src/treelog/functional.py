from typing import Dict, List

import inspect

from treelog.logger import TreeLogger, _CURRENT_BRANCH_IDS, _LIVE_BRANCHES
from treelog.logs import MessageType


# TODO: add support to putting tags on branches via the decorator
# TODO: Add support for putting metadata on branches via the decorator
# TODO: Add support for logging function calls, returns and exceptions
def _async_branch(func, tags=None, metadata=None):
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
            return _async_branch(func, tags=tags, metadata=metadata)
        else:
            return _sync_branch(func, tags=tags, metadata=metadata)

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


################################################################################


# TODO: add these to the branch wrapper in logger.py
def tree_log_exceptions(func):
    async def wrapper(*args, **kwargs):
        # First, find if there are any tree loggers in the arguments
        # or keyword arguments
        tree_loggers = [arg for arg in args if isinstance(arg, TreeLogger)] + [
            kwarg for kwarg in kwargs.values() if isinstance(kwarg, TreeLogger)
        ]
        # If there are no tree loggers, just run the function
        if not tree_loggers:
            return await func(*args, **kwargs)
        # Otherwise, run the function and log any exceptions
        else:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                for logger in tree_loggers:
                    await logger.log(str(e), MessageType.ERROR)
                raise e

    return wrapper


def tree_log_function_arguments_and_returns(func):
    async def wrapper(*args, **kwargs):
        # First, find if there are any tree loggers in the arguments
        # or keyword arguments
        tree_loggers = [arg for arg in args if isinstance(arg, TreeLogger)] + [
            kwarg for kwarg in kwargs.values() if isinstance(kwarg, TreeLogger)
        ]
        # If there are no tree loggers, just run the function
        if not tree_loggers:
            return await func(*args, **kwargs)
        # Otherwise, run the function and log the arguments and returns
        else:
            # Now format the args and kwargs like they are a function call
            function_call = f"{func.__name__}("
            for arg in args:
                function_call += f"{arg},\n"
            for key, value in kwargs.items():
                function_call += f"{key}={value},\n"
            function_call += ")"

            for logger in tree_loggers:
                await logger.log(f"Function call: {function_call}", MessageType.SYSTEM)

            result = await func(*args, **kwargs)

            for logger in tree_loggers:
                await logger.log(f"Function return: {result}", MessageType.SYSTEM)

            return result

    return wrapper


def tree_log(func):
    return tree_log_exceptions(tree_log_function_arguments_and_returns(func))
