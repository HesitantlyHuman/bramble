from typing import Any, Dict, List

import asyncio
import uuid
import datetime

from treelog.backend import (
    TreeLoggingWriter,
    TreeLoggingReader,
)
from treelog.logs import (
    MessageType,
    LogEntry,
)


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

    async def log(
        self,
        message: str,
        message_type: MessageType = MessageType.USER,
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
        timestamp = datetime.datetime.now().timestamp()
        log_entry = LogEntry(
            message=message,
            timestamp=timestamp,
            message_type=message_type,
            entry_metadata=entry_metadata,
        )
        await self.logging_writer.append_entry(flow_id=self.id, log_entry=log_entry)

    async def fork(self, name: str) -> "TreeLogger":
        """Fork a new tree logger from the current tree logger.

        Creates a new tree logger which can be use to log a new process which may run in
        parallel to the current process. Can be done multiple times to create multiple
        child loggers. The children will be linked to the parent logger and recorded in
        parent's logs.

        Args:
            name (str): The name of the new tree logger.

        Returns:
            TreeLogger: The new tree logger.
        """
        new_logger = TreeLogger(name=name, logging_writer=self.logging_writer)

        new_logger.add_parent(self.id)
        self.add_child(new_logger.id)

        await self.log(
            message=f"Forked logger: {new_logger.name}",
            message_type=MessageType.SYSTEM,
            entry_metadata=new_logger.logger_metadata(),
        )

        await asyncio.gather(
            self.update_logger_metadata(), new_logger.update_logger_metadata()
        )

        return new_logger

    async def add_metadata(self, metadata: Dict[str, str | int | float | bool]) -> None:
        self.user_metadata.update(metadata)
        await self.update_logger_metadata()

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

    async def update_logger_metadata(self) -> None:
        await self.logging_writer.update_logger_metadata(
            self.id, self.logger_metadata()
        )

    async def add_tags(self, tags: str | List[str]) -> None:
        await self.logging_writer.add_tags(self.id, tags=tags)

    @classmethod
    async def from_logging_storage(
        id: str, logging_writer: TreeLoggingWriter, logging_reader: TreeLoggingReader
    ) -> "TreeLogger":
        metadata = await logging_reader.get_logger_metadata(id)
        new_logger = TreeLogger(name=metadata["name"], logging_writer=logging_writer)
        new_logger.id = id
        new_logger.children = metadata["children"]
        new_logger.parents = metadata["parents"]
        return new_logger
