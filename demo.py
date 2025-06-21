import asyncio
import logging

import treelog


def entry_function():
    asyncio.run(async_entry())


@treelog.branch
async def async_entry():
    sync_inside()
    logging.info("Just some info, nothing to see here")
    asyncio.gather(*[async_a(), async_b(), async_b(), async_b()])


@treelog.branch
async def async_a():
    await async_b()

    await treelog.alog("Finished with async_b!", "USER", {"a": 1})

    asyncio.gather(*[async_b(), async_c()])


@treelog.branch
async def async_b():
    await treelog.alog("Started async_b", "ERROR")
    await async_c()
    logging.debug("I am a debug message!")


# TODO: figure out a better name for the decorator
@treelog.branch
async def async_c():
    await treelog.alog("First message")

    # Writing some stuff to a different file, should still write to the original as well
    logging_writer = treelog.FileTreeLoggingWriter("b")
    with treelog.TreeLogger("entry", logging_writer):
        await treelog.alog("Second message")
        await treelog.alog("Third message", entry_metadata={"id": "lkefidks"})

    sync_inside()

    print("I am printin some stuff man!")

    raise ValueError("Some random ass error")


@treelog.branch
def sync_inside():
    treelog.log("I am a sync message here inside async things")


logging_writer = treelog.FileTreeLoggingWriter("a")

with treelog.TreeLogger("entry", logging_writer=logging_writer):
    entry_function()

# No logging
entry_function()
