import bramble
import bramble.backends


# logging_writer = bramble.backends.FileWriter("test")
logging_writer = bramble.backends.RedisWriter.from_socket("127.0.0.1", "6379")
with bramble.TreeLogger(logging_backend=logging_writer) as logger:
    child = logger.root.branch("child")
    with child:
        bramble.log("Yay!")
    child.log("Yay!")  # If we close things on exit, this will not work....

# Where will our references to branches live?
# - _LIVE_BRANCHES
# - root of the TreeLogger

# The problem is that we don't know to remove things from live branches
