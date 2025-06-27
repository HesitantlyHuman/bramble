import asyncio
import logging
import treelog
import treelog.backends

# TODO: we should respect the set logging level somehow
# currently we override it, so that we can get all of the info
logging.basicConfig(level=logging.WARN)


def entry_function():
    asyncio.run(async_entry())


@treelog.branch
async def async_entry():
    sync_inside()
    logging.info("Just some info, nothing to see here")
    await asyncio.gather(*[async_a(), async_b(), async_b(), async_b()])


@treelog.branch(tags=["b"])
async def async_a():
    await async_b()

    treelog.log("Finished with async_b!", "USER", {"a": 1})

    logging.info("Another test")

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
    # logging_writer = treelog.FileTreeLoggingWriter("b")
    # with treelog.TreeLogger("entry", logging_writer):
    treelog.log("Second message")
    treelog.log("Third message", entry_metadata={"id": "lkefidks"})

    sync_inside()

    logging.info("EVEN MORE")

    print("I am printin some stuff man!")

    # raise ValueError("Some random ass error")


@treelog.branch
def sync_inside():
    treelog.log("I am a sync message here inside async things")
    logging.debug("You should really fix this")


logging_writer = treelog.backends.RedisWriter.from_socket("127.0.0.1", "6379")

with treelog.TreeLogger("entry", logging_backend=logging_writer) as logger:
    entry_function()

    print(logger.root.id)

# No logging
entry_function()
