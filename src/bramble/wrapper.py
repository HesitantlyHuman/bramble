from typing import Dict, List, Callable, Any, Awaitable

import functools
import inspect

from bramble.utils import (
    _stringify_function_call,
    _validate_tags_and_metadata,
)
from bramble.contextual import log, fork
from bramble.logs import MessageType

# _async_branch and _sync_branch are split into two functions this way so that
# we only call inspect.iscoroutinefunction a single time. We want the wrapper
# overhead to be as small as possible.


def _async_branch(func, tags=None, metadata=None):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            with fork(name=func.__name__, tags=tags, metadata=metadata):
                log(
                    "Function call:\n"
                    + _stringify_function_call(
                        func,
                        args,
                        kwargs,
                    ),
                    MessageType.SYSTEM,
                )

                output = await func(*args, **kwargs)

                try:
                    return_string = f"Function return:\n{output}"
                except Exception:
                    return_string = "Function return:\n`ERROR`"
                log(return_string, MessageType.SYSTEM)

                return output
        except Exception as e:
            log(e, MessageType.ERROR)
            raise e

    return wrapper


def _sync_branch(func, tags=None, metadata=None):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            with fork(name=func.__name__, tags=tags, metadata=metadata):
                log(
                    "Function call:\n"
                    + _stringify_function_call(
                        func,
                        args,
                        kwargs,
                    ),
                    MessageType.SYSTEM,
                )

                output = func(*args, **kwargs)

                try:
                    return_string = f"Function return:\n{output}"
                except Exception:
                    return_string = "Function return:\n`ERROR`"
                log(return_string, MessageType.SYSTEM)

                return output
        except Exception as e:
            log(e, MessageType.ERROR)
            raise e

    return wrapper


def branch(
    _func=None,
    *args,
    tags: List[str] | None = None,
    metadata: Dict[str, str | int | float | bool] | None = None,
) -> Callable[..., Any | Awaitable[Any]]:
    """Mark a function for branching.

    Using this decorator will mark a function for logging to branch anytime
    execution enters. Any bramble branches currently in context will create a
    new child, using their `branch` method. Logging that happens in this
    function will be added to the child branches.

    IMPORTANT: `branch` will not do anything if there are no bramble branches
    in the current context. You must use the TreeLogger context manager pattern
    if you wish `branch` to do anything.

    Args:
        *args: An optional list of tags and metadata to add to each branch for this function.
        tags (List[str], optional): An optional list of tags to add to each
            branch for this function.
        metadata: (Dict[str, str | int | float | bool], optional): An optional
            list of metadata to add to each branch for this function.
    """
    # We might have a tag or metadata arg that got passed as the first argument
    # (i.e. into _func), so we should check
    if _func is not None and not inspect.isfunction(_func):
        args = (_func, *args)
        _func = None

    tags, metadata = _validate_tags_and_metadata(
        *args,
        tags=tags,
        metadata=metadata,
    )

    @functools.wraps(_func)
    def _branch(func):
        if inspect.iscoroutinefunction(func):
            return _async_branch(
                func=func,
                tags=tags,
                metadata=metadata,
            )

        else:
            return _sync_branch(
                func=func,
                tags=tags,
                metadata=metadata,
            )

    if _func is None:
        return _branch
    else:
        return _branch(func=_func)
