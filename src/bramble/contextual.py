from typing import Dict, List, ContextManager

from contextlib import contextmanager, nullcontext

from bramble.utils import (
    _validate_log_call,
    _validate_tags_and_metadata,
)
from bramble.logs import MessageType
from bramble.loggers import (
    _CURRENT_BRANCH_IDS,
    _LIVE_BRANCHES,
    _ENABLED,
    LogBranch,
    _LoggingContext,
)


def log(
    message: str,
    message_type: MessageType | str = MessageType.USER,
    entry_metadata: Dict[str, str | int | float | bool] | None = None,
):
    """Log a message to the active `bramble` branches.

    Will log a message to any branches currently in context. Each
    branch will receive an identical log entry.

    IMPORTANT: `log` will not do anything if there are no bramble branches in
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
    message, message_type, entry_metadata = _validate_log_call(
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


def _set_tags_and_metadata(
    branches: List[LogBranch],
    tags: List[str] | None = None,
    metadata: Dict[str, str | int | float | bool] | None = None,
) -> None:
    for branch in branches:
        if tags is not None:
            branch.add_tags(tags)

        if metadata is not None:
            branch.add_metadata(metadata)


def apply(
    *args,
    tags: List[str] | None = None,
    metadata: Dict[str, str | int | float | bool] | None = None,
):
    """Add tags or metadata to active `bramble` branches.

    Will update the tags or metadata to any branches currently in context. Each
    branch will receive identical updates. If multiple lists of tags or
    dictionaries of metadata are supplied, they will be combined. All tags which
    are present in any list will be applied. Later dictionaries will be used to
    update earlier dictionaries. For example:

    ```
    apply(["a", "b"], ["b", "c"], {"a": 1, "b": 2}, {"b": 3})
    ```

    Would apply the tags `["a", "b", "c"]` and the metadata `{"a": 1, "b": 3}`.

    IMPORTANT: `apply` will not do anything if there are no bramble branches in
    the current context. You must use the TreeLogger context manager pattern if
    you wish `apply` to do anything.

    Args:
        *args: Arbitrary list of lists or dictionaries.
        tags (List[str] | None, optional): A list of tags to add to the current
            branches. Defaults to `None`.
        metadata (Dict[str, str | int | float | bool] | None, optional):
            Metadata to add to the current branches, defaults to `None`
    """

    if len(args) == 0 and tags is None and metadata is None:
        raise ValueError(f"Must provide at least one of `tags` or `metadata`.")

    tags, metadata = _validate_tags_and_metadata(
        *args,
        tags=tags,
        metadata=metadata,
    )

    current_branches = context()
    _set_tags_and_metadata(
        branches=current_branches,
        tags=tags,
        metadata=metadata,
    )


def context(*args: List[LogBranch] | None) -> List[LogBranch]:
    """Retrieve or set current `bramble` context.

    Either gets all branches from the current context, or if used as a context
    manager, sets provided branches as the current context.

    If no arguments are provided `context` will return the current context. If
    arguments are provided, they are expected to be either `LogBranch`s, or a
    list of `LogBranch`s.

    Example:
    ```
    current_context = bramble.context()
    new_context = [branch.branch("new") for branch in current_context]

    with bramble.context(new_context):
        ...
    ```

    Args:
        *args: Either one list of `LogBranch`s, or many `LogBranch`s, optional.

    Returns:
        (List[LogBranch] | ContextManager[None]): Either returns the current
            context, or a context manager in which the provided branches are the
            current context.
    """
    match len(args):
        case 0:
            branches = []

            current_branch_ids = _CURRENT_BRANCH_IDS.get()
            for id in current_branch_ids:
                branches.append(_LIVE_BRANCHES[id])

            return branches
        case 1:
            parameter = args[0]
            if isinstance(parameter, LogBranch):
                parameter = [parameter]

            if not isinstance(parameter, list):
                raise ValueError(
                    f"Arguments must either be of type `list` or `LogBranch`, received {type(parameter)}"
                )

            for element in parameter:
                if not isinstance(element, LogBranch):
                    raise ValueError(
                        f"All elements of list arguments must be of type `LogBranch`, received {type(element)}"
                    )
        case _:
            parameter = []
            for arg in args:
                if isinstance(arg, LogBranch):
                    parameter.append(arg)
                else:
                    raise ValueError(
                        f"If multiple arguments are provided, all arguments must be of type `LogBranch`, received {type(arg)}"
                    )

    if len(parameter) == 0:
        return nullcontext()

    return _LoggingContext(parameter)


def fork(
    name: str,
    tags: List[str] | None = None,
    metadata: Dict[str, str | int | float | bool] | None = None,
) -> ContextManager[None]:
    """Will fork the current `bramble` context.

    Creates new branches of any branches in the current context, using the
    provided name, and then sets the current context to those new branches,
    until the end of `fork`'s context. For use only as a context manager, if
    fork is not used as a context, then it will have no effect, other than
    creating new branches.

    Args:
        name (str): The name of this new context / branch.
        tags (List[str] | None, optional): A list of tags to add to the current
            branches. Defaults to `None`.
        metadata (Dict[str, str | int | float | bool] | None, optional):
            Metadata to add to the current branches, defaults to `None`
    """
    if not isinstance(name, str):
        raise ValueError(f"`name` must be of type `str`, received {type(name)}")

    tags, metadata = _validate_tags_and_metadata(tags=tags, metadata=metadata)

    current_context = context()

    if len(current_context) == 0:
        return nullcontext()

    next_context = [branch.branch(name) for branch in current_context]
    _set_tags_and_metadata(branches=next_context, tags=tags, metadata=metadata)

    return context(next_context)


@contextmanager
def disable() -> ContextManager[None]:  # type: ignore
    """Disables `bramble` logging.

    Will disable any `bramble` log calls from being run, until either
    `bramble.enable` is called, or the disable context ends. Can be used as
    either a single command, or as a context manager. Only the logging is
    disabled, all other `bramble` features, like creating branches, managing
    parents and children, and tracking logging contexts, will still function.
    """
    _ENABLED.set(False)
    yield
    _ENABLED.set(True)


def enable() -> None:
    """Enables `bramble` logging.

    Will enable `bramble` log calls. For use after a `bramble.disable` call.
    """
    _ENABLED.set(True)
