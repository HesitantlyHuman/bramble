import asyncio
import logging
import bramble
import bramble.backends


def entry_function():
    asyncio.run(async_entry())


@bramble.branch
async def async_entry():
    sync_inside()
    # If you log using standard python logging, each message may or may not be
    # present in the branch logs, depending on what level your python logger is
    # set to.
    logging.info("Just some info, nothing to see here")
    await asyncio.gather(*[async_a(), async_b(), async_b(), async_b()])


@bramble.branch(tags=["b"])
async def async_a():
    await async_b()

    bramble.log("Finished with async_b!", "USER", {"a": 1})

    # This will likely show up in the branch logs
    logging.warning("This is a warning")

    await asyncio.gather(*[async_b(), async_c()])


@bramble.branch({"a": 1})
async def async_b():
    bramble.log("Started async_b", "ERROR")
    await async_c()
    logging.debug("I am a debug message!")

    bramble.apply({"some tag": "some data"})


@bramble.branch
async def async_c():
    bramble.log("First message")

    # Writing some stuff to a different file, should still write to the original as well
    logging_writer = bramble.backends.FileWriter("b")
    with bramble.TreeLogger(logging_writer):
        bramble.log("Second message")
        bramble.log("Third message", entry_metadata={"id": "lkefidks"})

    sync_inside()

    # raise ValueError("Some random error")


@bramble.branch
def sync_inside():
    bramble.log("I am a sync message here inside async things")
    logging.debug("You should really fix this")


logging_writer = bramble.backends.FileWriter("test")

with bramble.TreeLogger(logging_backend=logging_writer):
    entry_function()

# No logging, all treelog functions are no-ops if there is not a logger
# currently in context.
entry_function()
