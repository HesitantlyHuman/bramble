import asyncio
import logging

import treelog


def entry_function():
    asyncio.run(async_entry())


@treelog.fork
async def async_entry():
    logging.info("Just some info, nothing to see here")
    asyncio.gather(*[async_a(), async_b(), async_b(), async_b()])


@treelog.fork
async def async_a():
    await async_b()

    treelog.log("Finished with async_b!", "USER", {"a": 1})

    asyncio.gather(*[async_b(), async_c()])


@treelog.fork
async def async_b():
    treelog.log("Started async_b", "ERROR")
    await async_c()
    logging.debug("I am a debug message!")


# TODO: figure out a better name for the decorator
@treelog.fork
async def async_c():
    treelog.log("First message")

    # Writing some stuff to a different file, should still write to the original as well
    logging_writer = treelog.FileTreeLoggingWriter()
    with treelog.TreeLogger("entry", logging_writer):
        treelog.log("Second message")
        treelog.log("Third message", entry_metadata={"id": "lkefidks"})

    print("I am printin some stuff man!")

    raise ValueError("Some random ass error")


logging_writer = treelog.FileTreeLoggingWriter()

with treelog.TreeLogger("entry", logging_writer=logging_writer):
    entry_function()

# No logging
entry_function()
