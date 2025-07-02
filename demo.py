import asyncio
import logging
import treelog
import treelog.backends


def entry_function():
    asyncio.run(async_entry())


@treelog.branch
async def async_entry():
    sync_inside()
    # If you log using standard python logging, each message may or may not be
    # present in the branch logs, depending on what level your python logger is
    # set to.
    logging.info("Just some info, nothing to see here")
    await asyncio.gather(*[async_a(), async_b(), async_b(), async_b()])


@treelog.branch(tags=["b"])
async def async_a():
    await async_b()

    treelog.log("Finished with async_b!", "USER", {"a": 1})

    # This will likely show up in the branch logs
    logging.warning("This is a warning")

    await asyncio.gather(*[async_b(), async_c()])


@treelog.branch(metadata={"a": 1})
async def async_b():
    treelog.log("Started async_b", "ERROR")
    await async_c()
    logging.debug("I am a debug message!")


@treelog.branch
async def async_c():
    treelog.log("First message")

    # Writing some stuff to a different file, should still write to the original as well
    logging_writer = treelog.backends.FileWriter("b")
    with treelog.TreeLogger("entry", logging_writer):
        treelog.log("Second message")
        treelog.log("Third message", entry_metadata={"id": "lkefidks"})

    sync_inside()

    raise ValueError("Some random error")


@treelog.branch
def sync_inside():
    treelog.log("I am a sync message here inside async things")
    logging.debug("You should really fix this")


logging_writer = treelog.backends.FileWriter("test")

with treelog.TreeLogger(logging_backend=logging_writer):
    entry_function()

# No logging, all treelog functions are no-ops if there is not a logger
# currently in context.
entry_function()
