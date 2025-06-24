import asyncio


# The issue with trying to just run this async (and not in another thread) is that someone could try to start the logger first, and then start an async loop (asyncio.run or something)


# But if we have the async batcher be a singleton, then each python process will only have 1, no matter how many async shenanigans they do. (How could we force there to only be one across threads as well?)
class LogBatcher:
    def __init__(self):
        self.queue = []

    async def _run(self):
        while True:
            pass

    def add_logging_task(self):
        pass
