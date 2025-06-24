from typing import Any, Dict, List, Set

import inspect
import contextvars
import datetime
import asyncio
import uuid

from treelog.backend import (
    TreeLoggingWriter,
    TreeLoggingReader,
)
from treelog.logs import (
    MessageType,
    LogEntry,
)

_LIVE_BRANCHES: Dict[str, "LogBranch"] = {}
_CURRENT_BRANCH_IDS: contextvars.ContextVar[Set[str] | None] = contextvars.ContextVar(
    "_CURRENT_BRANCH_IDS", default=set()
)


class TreeLogger:
    """A branching logger for async processes.

    A TreeLogger is a tree-like logger which can be used to log a flow of
    functions with many child functions. Will seperate each branch into its own
    log.
    """

    root: "LogBranch"

    def __init__(
        self,
        name: str,
        logging_backend: TreeLoggingWriter,
        debounce: float = 0.25,
        batch_size: int = 50,
    ):
        self.logging_backend = logging_backend

        self._log_tasks = []

        self.root = LogBranch(name=name, tree_logger=self)

        # TODO: start logging process

    async def _run():
        pass

    def log(
        self,
        branch_id: str,
        message: str,
        message_type: MessageType | str = MessageType.USER,
        entry_metadata: Dict[str, str | int | float | bool] = None,
    ) -> None:
        """Log a message to the tree logger.

        Args:
            message (str): The message to log.
            message_type (MessageType, optional): The type of the message. Defaults to
                MessageType.USER. Generally, MessageType.SYSTEM is used for system
                messages internal to the logging system.
            entry_metadata (Dict[str, Union[str, int, float, bool]], optional): Metadata
                to include with the log entry. Defaults to None.
        """
        if isinstance(message_type, str):
            message_type = MessageType.from_string(message_type)
        timestamp = datetime.datetime.now().timestamp()
        log_entry = LogEntry(
            message=message,
            timestamp=timestamp,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )
        self._log_tasks.append((branch_id, log_entry))

    def update_tree(self, branch_id: str, parent: str, children: List[str]) -> None:
        raise NotImplementedError()

    def update_metadata(
        self, branch_id: str, metadata: Dict[str, str | int | float | bool]
    ) -> None:
        raise NotImplementedError()

    def update_tags(self, branch_id: str, tags: List[str]) -> None:
        raise NotImplementedError()

    def __enter__(self):
        current_logger_ids = _CURRENT_BRANCH_IDS.get()

        if current_logger_ids is None:
            _CURRENT_BRANCH_IDS.set(set([self.root.id]))
        else:
            current_logger_ids.add(self.root.id)
            _CURRENT_BRANCH_IDS.set(current_logger_ids)

        _LIVE_BRANCHES[self.root.id] = self.root

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            # TODO: log the exception
            # TODO: create an exception logging util
            raise NotImplementedError()

        # Now, we need to remove ourselves from the current loggers, if we are
        # in them. Since we also know that we are the source of all branches
        # under us, we know that none of our children will still be in use via
        # the @treelog.branch API, so we can clean up ourselves and our children
        # from _LIVE_BRANCHES

        current_logger_ids = _CURRENT_BRANCH_IDS.get()
        try:
            current_logger_ids.remove(self.root.id)
            _CURRENT_BRANCH_IDS.set(current_logger_ids)
        except KeyError:
            pass

        keys_to_delete = [self.root.id]

        while keys_to_delete:
            next_key_to_delete = keys_to_delete.pop()
            try:
                logger_to_delete = _LIVE_BRANCHES.pop(next_key_to_delete)
                keys_to_delete.extend(logger_to_delete.children)
            except KeyError:
                pass


# TODO: add support to putting tags on branches via the decorator
# TODO: Add support for putting metadata on branches via the decorator
# TODO: Add support for logging function calls, returns and exceptions
def branch(func):
    def wrapper(*args, **kwargs):
        current_logger_ids = _CURRENT_BRANCH_IDS.get()

        if len(current_logger_ids) == 0:
            func(*args, **kwargs)

        new_logger_ids = set()
        for logger_id in current_logger_ids:
            old_logger = _LIVE_BRANCHES[logger_id]
            new_logger = old_logger.branch(name=func.__name__)
            _LIVE_BRANCHES[new_logger.id] = new_logger
            new_logger_ids.add(new_logger.id)
        _CURRENT_BRANCH_IDS.set(new_logger_ids)

        func(*args, **kwargs)

        _CURRENT_BRANCH_IDS.set(current_logger_ids)

    return wrapper


class LogBranch:
    id: str
    name: str
    parent: str
    children: List[str]
    tags: List[str]
    metadata: Dict[str, str | int | float | bool]

    def __init__(self, name: str, tree_logger: TreeLogger, id: str = None):
        self.name = name
        self.children = []
        self.parents = []
        self.tags = []
        self.metadata = {}

        self.tree_logger = tree_logger

        if id is None:
            id = str(uuid.uuid4().hex)[:24]
        self.id = id

    def log(
        self,
        message: str,
        message_type: MessageType | str = MessageType.USER,
        entry_metadata: Dict[str, str | int | float | bool] = None,
    ):
        """Log a message to the tree logger.

        Args:
            message (str): The message to log.
            message_type (MessageType, optional): The type of the message. Defaults to
                MessageType.USER. Generally, MessageType.SYSTEM is used for system
                messages internal to the logging system.
            entry_metadata (Dict[str, Union[str, int, float, bool]], optional): Metadata
                to include with the log entry. Defaults to None.
        """
        self.tree_logger.log(
            self.id,
            message=message,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )

    def branch(self, name: str) -> "LogBranch":
        """Create a new branch from the current.

        Creates a new branch which can be use to log seperately from the current
        branch. Can be done multiple times to create multiple child loggers. The
        children will be linked to the parent logger and recorded in parent's
        logs.

        Args:
            name (str): The name of the new tree logger.

        Returns:
            LogBranch: The new tree logger.
        """
        new_branch = LogBranch(
            name=name,
            tree_logger=self.tree_logger,
        )

        new_branch.set_parent(self.id)
        self.add_child(new_branch.id)

        # TODO: improve this log so that it is easier to link within the UI
        self.log(
            message=f"Branched Logger: {new_branch.name}",
            message_type=MessageType.SYSTEM,
            entry_metadata={"branch_id": new_branch.id},
        )

        return new_branch

    def add_child(self, child_id: str) -> None:
        self.children.append(child_id)
        self.tree_logger.update_tree(self.id, self.parent, self.children)

    def set_parent(self, parent_id: str) -> None:
        self.parent = parent_id
        self.tree_logger.update_tree(self.id, self.parent, self.children)

    def add_tags(self, tags: List[str]) -> None:
        self.tags.extend(tags)
        self.tree_logger.update_tags(self.id, self.tags)

    def add_metadata(self, metadata: Dict[str, str | int | float | bool]) -> None:
        self.metadata.update(metadata)
        self.tree_logger.update_metadata(self.id, self.metadata)

    # TODO: fix
    @classmethod
    def from_logging_storage(
        cls,
        id: str,
        logging_writer: TreeLoggingWriter,
        logging_reader: TreeLoggingReader,
    ) -> "LogBranch":
        metadata = logging_reader.get_logger_metadata(id)
        new_logger = LogBranch(name=metadata["name"], logging_writer=logging_writer)
        new_logger.id = id
        new_logger.children = metadata["children"]
        new_logger.parents = metadata["parents"]
        return new_logger


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
