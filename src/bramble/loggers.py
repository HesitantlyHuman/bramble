from typing import Set, Dict, List, Any, Tuple

import contextvars
import threading
import datetime
import asyncio
import queue
import time

from bramble.utils import _validate_log_call, _generate_id
from bramble.backends.base import BrambleBackend
from bramble.writer import BrambleWriter
from bramble.stdlib import hook_logging
from bramble.log_objects import (
    MessageType,
    LogEntry,
)

_LIVE_BRANCHES: Dict[str, "LogBranch"] = {}
_CURRENT_BRANCH_IDS: contextvars.ContextVar[Set[str]] = contextvars.ContextVar(
    "_CURRENT_BRANCH_IDS", default=set()
)
_ENABLED: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_ENABLED", default=True
)


# TODO: figure out how to nicely expose the BrambleWriter parameters
# TODO: Add closing of branches!!!
class TreeLogger:
    """A branching logger for async processes.

    A TreeLogger is a tree-like logger which can be used to log a flow of
    functions with many child functions. Will separate each branch into its own
    log.
    """

    root: "LogBranch"
    logging_backend: BrambleBackend
    logging_writer: BrambleWriter
    silent: bool

    def __init__(
        self,
        logging_backend: BrambleBackend,
        name: str = "entry",
        debounce: float = 0.25,
        batch_size: int = 50,
        silent: bool = False,
    ):
        if not isinstance(logging_backend, BrambleBackend):
            raise ValueError(
                f"`logging_backend` must be of type `BrambleBackend`, received {type(logging_backend)}."
            )

        if not isinstance(name, str):
            raise ValueError(f"`name` must be of type `str`, received {type(name)}.")

        self.logging_backend = logging_backend
        self.logging_writer = BrambleWriter(self.logging_backend)
        self.silent = silent

        self._tasks = queue.SimpleQueue()
        self._debounce = debounce
        self._batch_size = batch_size

        self.root = LogBranch(name=name, tree_logger=self)
        hook_logging()

    def run(self):
        async def _run():
            logging_tasks: Dict[str, List[LogEntry]] = None
            metadata_tasks: Dict[str, Dict[str, Any]] = None
            branch_creation_tasks: Set[Tuple[str, str]] = None

            deadline = None

            def get_batch_size():
                return max(
                    [0]
                    + [
                        len(item)
                        for item in [
                            logging_tasks,
                            metadata_tasks,
                            branch_creation_tasks,
                        ]
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

                            if not logging_tasks:
                                logging_tasks = {}

                            logging_tasks.setdefault(branch_id, []).append(log_entry)
                        case 1:
                            _, branch_id, parent, children = task

                            if not metadata_tasks:
                                metadata_tasks = {}

                            metadata_tasks.setdefault(branch_id, {})["parent"] = parent
                            metadata_tasks.setdefault(branch_id, {}).setdefault(
                                "children", set()
                            ).update(children)
                        case 2:
                            _, branch_id, metadata = task

                            if not metadata_tasks:
                                metadata_tasks = {}

                            metadata_tasks.setdefault(branch_id, {}).setdefault(
                                "metadata", {}
                            ).update(metadata)
                        case 3:
                            _, branch_id, tags = task

                            if not metadata_tasks:
                                metadata_tasks = {}

                            metadata_tasks.setdefault(branch_id, {}).setdefault(
                                "tags", set()
                            ).update(tags)
                        case 4:
                            _, branch_id, name = task

                            if not branch_creation_tasks:
                                branch_creation_tasks = set()

                            branch_creation_tasks.add((branch_id, name))

                if (
                    time.time() > deadline
                    or get_batch_size() >= self._batch_size
                    or task is None
                ):
                    if branch_creation_tasks:
                        await self.logging_writer.add_branches(branch_creation_tasks)

                    todo = []

                    if logging_tasks:
                        todo.append(
                            self.logging_writer.append_entries(
                                entries=logging_tasks,
                            )
                        )

                    if metadata_tasks:
                        todo.append(
                            self.logging_writer.update_branch_info(
                                parents=metadata_tasks["parent"],
                                children=metadata_tasks["children"],
                                tags=metadata_tasks["tags"],
                                metadata=metadata_tasks["metadata"],
                            )
                        )

                    await asyncio.gather(*todo)

                    logging_tasks, metadata_tasks, branch_creation_tasks = (
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
        message, message_type, entry_metadata = _validate_log_call(
            message=message,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )

        if not _ENABLED.get():
            return

        timestamp = datetime.datetime.now().timestamp()
        log_entry = LogEntry(
            message=message,
            timestamp=timestamp,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )
        self._tasks.put((0, branch_id, log_entry))

    def _update_tree(self, branch_id: str, parent: str, children: Set[str]) -> None:
        self._tasks.put((1, branch_id, parent, children))

    def _update_metadata(
        self, branch_id: str, metadata: Dict[str, str | int | float | bool]
    ) -> None:
        self._tasks.put((2, branch_id, metadata))

    def _update_tags(self, branch_id: str, tags: Set[str]) -> None:
        self._tasks.put((3, branch_id, tags))

    def _create_branch(self, branch_id: str, name: str) -> None:
        self._tasks.put((4, branch_id, name))

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
        # the @bramble.branch API, so we can clean up ourselves and our
        # children from _LIVE_BRANCHES

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
    children: Set[str]
    tags: Set[str]
    metadata: Dict[str, str | int | float | bool]

    slots = (
        "id",
        "name",
        "parent",
        "children",
        "tags",
        "metadata",
        "tree_logger",
    )

    def __init__(self, name: str, tree_logger: TreeLogger, id: str = None):
        self.name = name
        self.parent = None
        self.children = set()
        self.tags = set()
        self.metadata = {"name": name}

        self.tree_logger = tree_logger

        if id is None:
            id = _generate_id("b")
        self.id = id

        self.tree_logger._update_metadata(self.id, self.metadata)
        self.tree_logger._create_branch(self.id, self.name)

    def log(
        self,
        message: str | Exception,
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

    # TODO: typecheck this
    def branch(self, name: str) -> "LogBranch":
        """Create a new branch from the current.

        Creates a new branch which can be use to log separately from the current
        branch. Can be done multiple times to create multiple child loggers. The
        children will be linked to the parent logger and recorded in parent's
        logs.

        Args:
            name (str): The name of the new tree logger.

        Returns:
            LogBranch: The new `bramble` branch.
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
        if not isinstance(child_id, str):
            raise ValueError(
                f"`child_id` must be of type `str`, received {type(child_id)}."
            )
        self.children.add(child_id)
        self.tree_logger._update_tree(self.id, self.parent, self.children)

    def set_parent(self, parent_id: str) -> None:
        if not isinstance(parent_id, str):
            raise ValueError(
                f"`parent_id` must be of type `str`, received {type(parent_id)}."
            )
        self.parent = parent_id
        self.tree_logger._update_tree(self.id, self.parent, self.children)

    def add_tags(self, tags: List[str]) -> None:
        if not isinstance(tags, list):
            raise ValueError(f"`tags` must be of type `list`, received {type(tags)}.")
        for tag in tags:
            if not isinstance(tag, str):
                raise ValueError(
                    f"Each entry of `tags` must be of type `str`, received {type(tag)}."
                )
        self.tags.update(tags)
        self.tree_logger._update_tags(self.id, self.tags)

    def add_metadata(self, metadata: Dict[str, str | int | float | bool]) -> None:
        if not isinstance(metadata, dict):
            raise ValueError(
                f"`metadata` must be of type `dict`, received {type(metadata)}"
            )
        for key, value in metadata.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"`metadata` must have keys of type `str`, received {type(key)}"
                )
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(
                    f"`metadata` must have values of type `str`, `int`, `float`, or `bool`, received {type(value)}"
                )
        self.metadata.update(metadata)
        self.tree_logger._update_metadata(self.id, self.metadata)

    def __repr__(self):
        return f"LogBranch(id={self.id}, name={self.name}, parent={self.parent}, children={self.children}, tags={self.tags}, metadata={self.metadata})"

    def __enter__(self):
        self._logging_context = _LoggingContext(new_branches=[self])
        self._logging_context.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self._logging_context.__exit__(exc_type, exc_value, traceback)


class _LoggingContext:
    _prev_logger_ids: Set[str]
    _new_branches: List[LogBranch]

    __slots__ = ("_prev_logger_ids", "_new_branches")

    def __init__(self, new_branches: List[LogBranch]):
        self._new_branches = new_branches

    def __enter__(self):
        self._prev_logger_ids = _CURRENT_BRANCH_IDS.get()

        _LIVE_BRANCHES.update({branch.id: branch for branch in self._new_branches})
        _CURRENT_BRANCH_IDS.set({branch.id for branch in self._new_branches})

    def __exit__(self, exc_type, exc_value, traceback):
        _CURRENT_BRANCH_IDS.set(self._prev_logger_ids)
