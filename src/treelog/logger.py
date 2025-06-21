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
from treelog.utils import dispatch_async

LOGGERS: Dict[str, "TreeLogger"] = {}
CURRENT_LOGGER_IDS: contextvars.ContextVar[Set[str] | None] = contextvars.ContextVar(
    "CURRENT_LOGGER_IDS", default=set()
)


def _branch_async(func):
    async def wrapper(*args, **kwargs):
        current_logger_ids = CURRENT_LOGGER_IDS.get()

        if len(current_logger_ids) == 0:
            await func(*args, **kwargs)

        print(current_logger_ids)
        print(LOGGERS)

        new_logger_ids = set()
        for logger_id in current_logger_ids:
            old_logger = LOGGERS[logger_id]
            new_logger = await old_logger.async_branch(name=func.__name__)
            LOGGERS[new_logger.id] = new_logger
            new_logger_ids.add(new_logger.id)
        CURRENT_LOGGER_IDS.set(new_logger_ids)

        print("running function")

        await func(*args, **kwargs)

        CURRENT_LOGGER_IDS.set(current_logger_ids)

    return wrapper


def _branch_sync(func):
    def wrapper(*args, **kwargs):
        current_logger_ids = CURRENT_LOGGER_IDS.get()

        if len(current_logger_ids) == 0:
            func(*args, **kwargs)

        new_logger_ids = set()
        for logger_id in current_logger_ids:
            old_logger = LOGGERS[logger_id]
            new_logger = old_logger.branch(name=func.__name__)
            LOGGERS[new_logger.id] = new_logger
            new_logger_ids.add(new_logger.id)
        CURRENT_LOGGER_IDS.set(new_logger_ids)

        func(*args, **kwargs)

        CURRENT_LOGGER_IDS.set(current_logger_ids)

    return wrapper


def branch(func):
    if inspect.iscoroutinefunction(func):
        return _branch_async(func)
    else:
        return _branch_sync(func)


class TreeLogger:
    """A branching logger for async processes.

    The TreeLogger is a tree-like logger which can be used to log a flow of processes
    with many child processes.
    """

    id: str
    name: str
    children: List[str]
    parents: List[str]

    def __init__(self, name: str, logging_writer: TreeLoggingWriter, id: str = None):
        self.name = name
        self.children = []
        self.parents = []
        self.logging_writer = logging_writer
        self.user_metadata = {}

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
        print("Trying to log sync")
        dispatch_async(
            self.alog,
            message=message,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )
        print("Finished logging sync")

    async def alog(
        self,
        message: str,
        message_type: MessageType | str = MessageType.USER,
        entry_metadata: Dict[str, str | int | float | bool] = None,
    ):
        """Log a message to the tree logger.

        Args:
            message (`str`): The message to log.
            message_type (`MessageType | str`, optional): The type of the message. Defaults to
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
        print("Created entry to add to logging writer")
        await self.logging_writer.append_entry(flow_id=self.id, log_entry=log_entry)
        print("Successfully added entry to logging writer")

    def branch(self, name: str) -> "TreeLogger":
        """Branch a new tree logger from the current tree logger.

        Creates a new tree logger which can be use to log a new process which may run in
        parallel to the current process. Can be done multiple times to create multiple
        child loggers. The children will be linked to the parent logger and recorded in
        parent's logs.

        Args:
            name (str): The name of the new tree logger.

        Returns:
            TreeLogger: The new tree logger.
        """
        return dispatch_async(self.async_branch, name=name)

    async def async_branch(self, name: str) -> "TreeLogger":
        """Branch a new tree logger from the current tree logger.

        Creates a new tree logger which can be use to log a new process which may run in
        parallel to the current process. Can be done multiple times to create multiple
        child loggers. The children will be linked to the parent logger and recorded in
        parent's logs.

        Args:
            name (str): The name of the new tree logger.

        Returns:
            TreeLogger: The new tree logger.
        """
        print(f"Branching logger into function: '{name}'")
        new_logger = TreeLogger(name=name, logging_writer=self.logging_writer)

        new_logger.add_parent(self.id)
        self.add_child(new_logger.id)

        await self.log(
            message=f"Branched Logger: {new_logger.name}",
            message_type=MessageType.SYSTEM,
            entry_metadata=new_logger.logger_metadata(),
        )

        await asyncio.gather(
            self.update_logger_metadata(), new_logger.update_logger_metadata()
        )

        return new_logger

    def add_child(self, child_id: str) -> None:
        self.children.append(child_id)

    def add_parent(self, parent_id: str) -> None:
        self.parents.append(parent_id)

    def logger_metadata(self) -> Dict[str, Any]:
        base_metadata = {
            "name": self.name,
            "parents": self.parents,
            "children": self.children,
        }
        base_metadata.update(self.user_metadata)
        return base_metadata

    def update_logger_metadata(self) -> None:
        dispatch_async(self.async_update_logger_metadata)

    async def async_update_logger_metadata(self) -> None:
        await self.logging_writer.async_update_logger_metadata(
            self.id, self.logger_metadata()
        )

    def add_metadata(self, metadata: Dict[str, str | int | float | bool]) -> None:
        dispatch_async(self.async_add_metadata, metadata=metadata)

    async def async_add_metadata(
        self, metadata: Dict[str, str | int | float | bool]
    ) -> None:
        self.user_metadata.update(metadata)
        await self.async_update_logger_metadata()

    def add_tags(self, tags: str | List[str]) -> None:
        dispatch_async(self.async_add_tags, tags=tags)

    async def async_add_tags(self, tags: str | List[str]) -> None:
        await self.logging_writer.async_add_tags(self.id, tags=tags)

    @classmethod
    def from_logging_storage(
        cls,
        id: str,
        logging_writer: TreeLoggingWriter,
        logging_reader: TreeLoggingReader,
    ) -> "TreeLogger":
        return dispatch_async(
            cls.async_from_logging_storage,
            id=id,
            logging_writer=logging_writer,
            logging_reader=logging_reader,
        )

    @classmethod
    async def async_from_logging_storage(
        cls,
        id: str,
        logging_writer: TreeLoggingWriter,
        logging_reader: TreeLoggingReader,
    ) -> "TreeLogger":
        metadata = await logging_reader.async_get_logger_metadata(id)
        new_logger = TreeLogger(name=metadata["name"], logging_writer=logging_writer)
        new_logger.id = id
        new_logger.children = metadata["children"]
        new_logger.parents = metadata["parents"]
        return new_logger

    def __enter__(self):
        current_logger_ids = CURRENT_LOGGER_IDS.get()

        if current_logger_ids is None:
            CURRENT_LOGGER_IDS.set(set([self.id]))
        else:
            current_logger_ids.add(self.id)
            CURRENT_LOGGER_IDS.set(current_logger_ids)

        LOGGERS[self.id] = self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            # TODO: log the exception
            raise NotImplementedError()

        # Now, we need to remove ourselves from the current loggers, if we are
        # in them. Since we also know that we are the source of all branches
        # under us, we know that none of our children will still be in use via
        # the @treelog.branch API, so we can clean up ourselves and our children
        # from LOGGERS

        current_logger_ids = CURRENT_LOGGER_IDS.get()
        try:
            current_logger_ids.remove(self.id)
            CURRENT_LOGGER_IDS.set(current_logger_ids)
        except KeyError:
            pass

        keys_to_delete = [self.id]

        while keys_to_delete:
            next_key_to_delete = keys_to_delete.pop()
            try:
                logger_to_delete = LOGGERS.pop(next_key_to_delete)
                keys_to_delete.extend(logger_to_delete.children)
            except KeyError:
                pass


def log(
    message: str,
    message_type: MessageType | str = MessageType.USER,
    entry_metadata: Dict[str, str | int | float | bool] | None = None,
):
    current_logger_ids = CURRENT_LOGGER_IDS.get()
    if current_logger_ids is None:
        return

    for logger_id in current_logger_ids:
        logger = LOGGERS[logger_id]
        logger.log(
            message=message, message_type=message_type, entry_metadata=entry_metadata
        )


async def alog(
    message: str,
    message_type: MessageType | str = MessageType.USER,
    entry_metadata: Dict[str, str | int | float | bool] | None = None,
):
    current_logger_ids = CURRENT_LOGGER_IDS.get()
    if current_logger_ids is None:
        return

    logging_tasks = []
    for logger_id in current_logger_ids:
        logger = LOGGERS[logger_id]
        logging_tasks.append(
            logger.alog(
                message=message,
                message_type=message_type,
                entry_metadata=entry_metadata,
            )
        )
    asyncio.gather(*logging_tasks)
