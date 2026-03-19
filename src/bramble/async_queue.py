from typing import Generic, TypeVar, List, Callable, Awaitable

import asyncio
import queue
import time

T = TypeVar("T")


def active_tasks() -> int:
    return len([task for task in asyncio.all_tasks() if not task.done()])


class BatchingQueue(Generic[T]):  # TODO: come up w better name
    batch_size: int
    debounce: float

    def __init__(
        self,
        batch_size: int,
        debounce: float,
        output_callback: Callable[[List[T]], Awaitable[None]],
    ):
        self.batch_size = batch_size
        self.debounce = debounce
        self.output_callback = output_callback

        self._event_loop = None
        try:
            self._event_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        self._batch: List[T] = []
        self._batch_baton: asyncio.Future | None = None
        self._current_batch_deadline: float | None = None

    def add(self, item: T, timeout: float = None) -> None:
        # Should add an item if space, otherwise block until timeout or we can add the item
        # Should raise TimeoutError
        pass

    async def async_add(self, item: T, timeout: float = None) -> None:
        # Should add an item if space, otherwise wait until timeout or we can add the item
        # Should raise TimeoutError
        if timeout is not None:
            cutoff_time = time.monotonic() + timeout
        else:
            cutoff_time = None

        # Wait for batch to be open
        while True:
            if self._batch_baton is None or len(self._batch) < self.batch_size:
                break
            if cutoff_time is not None and time.monotonic() > cutoff_time:
                raise TimeoutError()  # TODO: better error
            # Wait until the batch is done, or our cutuff is due
            if cutoff_time is not None:
                remaining = cutoff_time - time.monotonic()
            else:
                remaining = None
            await asyncio.wait([self._batch_baton], timeout=remaining)

        # Now that the batch is open, we don't want to do any waiting before
        # handling adding ourselves to the batch

        if self._batch_baton is None:
            if self._event_loop is None:
                self._event_loop = asyncio.get_running_loop()
            self._batch_baton = self._event_loop.create_future()
            self._batch.append(item)
            self._current_batch_deadline = time.monotonic() + self.debounce
        elif len(self._batch) < self.batch_size:
            # Pass the baton
            self._batch_baton.set_result(None)
            self._batch_baton = self._event_loop.create_future()
            self._batch.append(item)

        async def _output_batch():
            batch = self._batch
            self._batch = []
            self._batch_baton = None
            self._current_batch_deadline = None
            await self.output_batch(batch)  # TODO: what to do if this raises?

        if len(self._batch) >= self.batch_size:
            # The batch needs to be written
            await _output_batch()
            return

        # Now wait for the debounce to be up, or the baton to pass
        batch_debounce_remaining = self._current_batch_deadline - time.monotonic()
        done, _ = await asyncio.wait(
            [self._batch_baton], timeout=batch_debounce_remaining
        )

        if len(done) > 0:
            # The baton has been passed
            return
        else:
            # The batch needs to be written
            await _output_batch()

    async def output_batch(self, batch: List[T]):
        # print(f"({time.monotonic()}) Outputting batch of size {len(batch)}")
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    my_queue: BatchingQueue[int] = BatchingQueue(
        batch_size=10, debounce=1, output_callback=None
    )

    async def main():
        # for i in range(100):
        #     await my_queue.async_add(i)
        start = time.time()
        tasks = []
        for i in range(100_003):
            tasks.append(my_queue.async_add(i))
        await asyncio.gather(*tasks)
        end = time.time()
        print(end - start)

    asyncio.run(main())
