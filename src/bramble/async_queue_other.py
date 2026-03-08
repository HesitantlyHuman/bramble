from typing import Generic, TypeVar, Callable, Awaitable, List
import asyncio
import time

T = TypeVar("T")


class BatchingQueue(Generic[T]):
    def __init__(
        self,
        batch_size: int,
        debounce: float,
        output_callback: Callable[[List[T]], Awaitable[None]],
        max_pending_items: int = 100,
    ):
        self.batch_size = batch_size
        self.debounce = debounce
        self.output_callback = output_callback
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=max_pending_items)
        self._runner_task: asyncio.Task | None = None
        self._closed = False

    def start(self) -> None:
        if self._runner_task is None:
            self._runner_task = asyncio.create_task(self._run_batcher())

    async def close(self) -> None:
        self._closed = True
        await self._runner_task

    async def async_add(self, item: T, timeout: float | None = None) -> None:
        if self._closed:
            raise RuntimeError("BatchingQueue is closed")

        if self._runner_task is None:
            self.start()

        if timeout is None:
            await self._queue.put(item)
        else:
            await asyncio.wait_for(self._queue.put(item), timeout=timeout)

    async def _run_batcher(self) -> None:
        while True:
            if self._closed and self._queue.empty():
                return

            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=1)
            except asyncio.TimeoutError:
                continue

            batch = [item]
            deadline = time.monotonic() + self.debounce

            while len(batch) < self.batch_size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break

                try:
                    item = await asyncio.wait_for(self._queue.get(), timeout=remaining)
                except asyncio.TimeoutError:
                    break

                batch.append(item)

            await self.output_callback(batch)


if __name__ == "__main__":
    handled = 0
    num = 100_003

    async def callback(batch: List[int]):
        handled += len(batch)
        print(f"({time.monotonic()}) Outputting batch of size {len(batch)}")

    my_queue: BatchingQueue[int] = BatchingQueue(
        batch_size=10, debounce=1, output_callback=callback
    )

    async def main():
        # for i in range(100):
        #     await my_queue.async_add(i)
        tasks = []
        for i in range(num):
            tasks.append(my_queue.async_add(i))
        await asyncio.gather(*tasks)
        await my_queue.close()
        print(f"Handled {handled}/{num} items.")

    asyncio.run(main())
