from typing import Any, Dict, List, Set

import threading
import datetime
import asyncio
import queue
import uuid
import time

from treelog.context import _LIVE_BRANCHES, _CURRENT_BRANCH_IDS
from treelog.utils import validate_log_call
from treelog.backend import TreeLogWriter
from treelog.stdlib import hook_logging
from treelog.logs import (
    MessageType,
    LogEntry,
)


class TreeLogger:
    """A branching logger for async processes.

    A TreeLogger is a tree-like logger which can be used to log a flow of
    functions with many child functions. Will seperate each branch into its own
    log.
    """

    root: "LogBranch"
    logging_backend: TreeLogWriter
    silent: bool

    def __init__(
        self,
        name: str,
        logging_backend: TreeLogWriter,
        debounce: float = 0.25,
        batch_size: int = 50,
        silent: bool = False,
    ):
        self.logging_backend = logging_backend
        self.silent = silent

        self._tasks = queue.SimpleQueue()
        self._debounce = debounce
        self._batch_size = batch_size

        self.root = LogBranch(name=name, tree_logger=self)
        hook_logging()

    def run(self):
        async def _run():
            log_tasks, tree_tasks, meta_tasks, tag_tasks = (
                None,
                None,
                None,
                None,
            )

            deadline = None

            def get_batch_size():
                return max(
                    [0]
                    + [
                        len(item)
                        for item in [log_tasks, tree_tasks, meta_tasks, tag_tasks]
                        if item is not None
                    ]
                )

            while True:
                if deadline:
                    try:
                        task = self._tasks.get(timeout=deadline - time.time())
                    except queue.Empty:
                        task = ()
                else:
                    task = self._tasks.get()
                    deadline = time.time() + self._debounce

                if task is not None and len(task) > 0:
                    task_type = task[0]
                    match task_type:
                        case 0:
                            _, branch_id, log_entry = task

                            if not log_tasks:
                                log_tasks = {}

                            if not branch_id in log_tasks:
                                log_tasks[branch_id] = []

                            log_tasks[branch_id].append(log_entry)
                        case 1:
                            _, branch_id, parent, children = task

                            if not tree_tasks:
                                tree_tasks = {}

                            tree_tasks[branch_id] = (parent, list(set(children)))
                        case 2:
                            _, branch_id, metadata = task

                            if not meta_tasks:
                                meta_tasks = {}

                            if not branch_id in meta_tasks:
                                meta_tasks[branch_id] = {}

                            meta_tasks[branch_id].update(metadata)
                        case 3:
                            _, branch_id, tags = task

                            if not tag_tasks:
                                tag_tasks = {}

                            if not branch_id in tag_tasks:
                                tag_tasks[branch_id] = []

                            task_tags = set(tag_tasks[branch_id])
                            task_tags.update(tags)
                            tag_tasks[branch_id] = list(task_tags)

                if (
                    time.time() > deadline
                    or get_batch_size() >= self._batch_size
                    or task is None
                ):
                    todo = []

                    if log_tasks:
                        todo.append(
                            self.logging_backend.async_append_entries(
                                entries=log_tasks,
                            )
                        )

                    if tree_tasks:
                        todo.append(
                            self.logging_backend.async_update_tree(
                                relationships=tree_tasks,
                            )
                        )

                    if meta_tasks:
                        todo.append(
                            self.logging_backend.async_update_branch_metadata(
                                metadata=meta_tasks,
                            )
                        )

                    if tag_tasks:
                        todo.append(
                            self.logging_backend.async_add_tags(
                                tags=tag_tasks,
                            )
                        )

                    await asyncio.gather(*todo)

                    log_tasks, tree_tasks, meta_tasks, tag_tasks = (
                        None,
                        None,
                        None,
                        None,
                    )

                    deadline = None

                if task is None:
                    return

        try:
            asyncio.run(_run())
        except Exception as e:
            # TODO: make this error easier to understand
            if not self.silent:
                raise e

    def log(
        self,
        branch_id: str,
        message: str | Exception,
        message_type: MessageType | str = MessageType.USER,
        entry_metadata: Dict[str, str | int | float | bool] | None = None,
    ) -> None:
        """Log a message to the tree logger.

        Args:
            branch_id (str): ID of the branch to log this message to.
            message (str): The message to log.
            message_type (MessageType | str, optional): The type of the message.
                Defaults to MessageType.USER. Generally, MessageType.SYSTEM is
                used for system messages internal to the logging system. If a
                string is passed, an attempt is made to cast it to MessageType.
            entry_metadata (Dict[str, Union[str, int, float, bool]], optional):
                Metadata to include with the log entry. Defaults to None.

        Raises:
            ValueError: If `message` is not a string, `message_type` cannot be
                converted to a MessageType, `entry_metadata` is not a
                dictionary or is not None, the keys of `entry_metadata` are not
                strings, or the values of `entry_metadata` are not `str`, `int`,
                `float`, or `bool`.
        """
        message, message_type, entry_metadata = validate_log_call(
            message=message,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )

        timestamp = datetime.datetime.now().timestamp()
        log_entry = LogEntry(
            message=message,
            timestamp=timestamp,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )
        self._tasks.put((0, branch_id, log_entry))

    def update_tree(self, branch_id: str, parent: str, children: List[str]) -> None:
        self._tasks.put((1, branch_id, parent, children))

    def update_metadata(
        self, branch_id: str, metadata: Dict[str, str | int | float | bool]
    ) -> None:
        self._tasks.put((2, branch_id, metadata))

    def update_tags(self, branch_id: str, tags: List[str]) -> None:
        self._tasks.put((3, branch_id, tags))

    def __enter__(self):
        current_logger_ids = _CURRENT_BRANCH_IDS.get()

        if current_logger_ids is None:
            _CURRENT_BRANCH_IDS.set(set([self.root.id]))
        else:
            current_logger_ids.add(self.root.id)
            _CURRENT_BRANCH_IDS.set(current_logger_ids)

        _LIVE_BRANCHES[self.root.id] = self.root

        self._logging_thread = threading.Thread(target=self.run)
        self._logging_thread.start()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            try:
                self.root.log(exc_value, "ERROR")
            except:
                pass

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

        # Stop the logging thread
        self._tasks.put(None)
        self._logging_thread.join()


class LogBranch:
    id: str
    name: str
    parent: str | None
    children: List[str]
    tags: List[str]
    metadata: Dict[str, str | int | float | bool]

    def __init__(self, name: str, tree_logger: TreeLogger, id: str = None):
        self.name = name
        self.parent = None
        self.children = []
        self.tags = []
        self.metadata = {"name": name}

        self.tree_logger = tree_logger

        if id is None:
            id = str(uuid.uuid4().hex)[:24]
        self.id = id

        self.tree_logger.update_metadata(self.id, self.metadata)

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

        self.log(
            message=f"Branched Logger: `{new_branch.name}`",
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
