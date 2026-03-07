from typing import Generic, TypeVar, List, Callable, Awaitable

import asyncio
import queue

T = TypeVar("T")


class BatchingQueue(Generic[T]):
    batch_size: int
    debounce: float

    _queue: queue.SimpleQueue
    _output_task: asyncio.Task | None
    _task_is_full: bool

    def __init__(
        self,
        batch_size: int,
        debounce: float,
        output_callback: Callable[[List[T]], Awaitable[None]],
    ):
        self.batch_size = batch_size
        self.debounce = debounce
        self.output_callback = output_callback
        self._output_task = None
        self._task_is_full = False

    def add(self, item: T, timeout: float = None) -> None:
        # Should add an item if space, otherwise block until timeout or we can add the item
        # Should raise TimeoutError
        pass

    async def async_add(self, item: T, timeout: float = None) -> None:
        # Should add an item if space, otherwise wait until timeout or we can add the item
        # Should raise TimeoutError
        self._queue.put(item=item)
        if not self._task_is_full and self._output_task is not None:
            self._output_task.cancel()

    async def output_batch(self, timeout: float = None):
        pass
