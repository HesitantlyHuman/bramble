from __future__ import annotations

from typing import Generic, TypeVar, Callable, Awaitable, List
from collections import deque
import asyncio

T = TypeVar("T")


class BatchingQueue(Generic[T]):
    def __init__(
        self,
        batch_size: int,
        debounce: float,
        output_callback: Callable[[List[T]], Awaitable[None]],
        max_pending_items: int | None = 100,
    ):
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if debounce < 0:
            raise ValueError("debounce must be >= 0")
        if max_pending_items is not None and max_pending_items <= 0:
            raise ValueError("max_pending_items must be > 0 or None")

        self.batch_size = batch_size
        self.debounce = debounce
        self.output_callback = output_callback

        self._items: deque[T] = deque()
        self._items_available: asyncio.Event = asyncio.Event()
        self._runner_task: asyncio.Task[None] | None = None
        self._closed = False

        self._slots: asyncio.Semaphore | None = (
            None if max_pending_items is None else asyncio.Semaphore(max_pending_items)
        )

    def start(self) -> None:
        if self._runner_task is None:
            self._runner_task = asyncio.create_task(self._run_batcher())

    async def close(self) -> None:
        if self._runner_task is None:
            self._closed = True
            return

        self._closed = True
        await self._runner_task

    async def async_add(self, item: T, timeout: float | None = None) -> None:
        if self._closed:
            raise RuntimeError("BatchingQueue is closed")

        if self._runner_task is None:
            self.start()

        acquired_slot = False
        try:
            if self._slots is not None:
                if timeout is None:
                    await self._slots.acquire()
                else:
                    await asyncio.wait_for(self._slots.acquire(), timeout=timeout)
                acquired_slot = True

            self._items.append(item)
            self._items_available.set()
        except Exception:
            if acquired_slot and self._slots is not None:
                self._slots.release()
            raise

    async def _run_batcher(self) -> None:
        loop = asyncio.get_running_loop()

        while True:
            await self._items_available.wait()

            while len(self._items) > 0:
                batch: List[T] = [self._items.popleft()]
                if self._slots is not None:
                    self._slots.release()

                deadline = loop.time() + self.debounce

                while len(batch) < self.batch_size:
                    while len(self._items) > 0 and len(batch) < self.batch_size:
                        batch.append(self._items.popleft())
                        if self._slots is not None:
                            self._slots.release()

                    if len(batch) >= self.batch_size:
                        break

                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        break

                    try:
                        await asyncio.wait_for(
                            self._items_available.wait(), timeout=remaining
                        )
                    except asyncio.TimeoutError:
                        break

                await self.output_callback(batch)
            self._items_available.clear()

            if self._closed:
                return


if __name__ == "__main__":
    import time

    handled = 0
    num = 100_003

    async def callback(batch: List[int]) -> None:
        global handled
        handled += len(batch)
        await asyncio.sleep(0.1)

    my_queue: BatchingQueue[int] = BatchingQueue(
        batch_size=10,
        debounce=1.0,
        output_callback=callback,
        max_pending_items=100,
    )

    async def main() -> None:
        start = time.time()
        await asyncio.gather(*(my_queue.async_add(i) for i in range(num)))
        await my_queue.close()
        end = time.time()
        print(end - start)
        print(f"Handled {handled}/{num}")

    asyncio.run(main())
