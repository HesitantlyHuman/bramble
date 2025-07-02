import treelog
import treelog.backends

import traceback

logging_writer = treelog.backends.FileWriter("test")


@treelog.branch
def a_function():
    raise ValueError("this is a test!")


with treelog.TreeLogger("entry", logging_backend=logging_writer) as logger:
    a_function()
