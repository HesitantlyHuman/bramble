import asyncio


# TODO: Figure out how to do this correctly. How do we handle when we are using
# the TreeLoggers in a sync function?
def dispatch_async(async_func, *args, **kwargs):
    """Runs an async function inside non-async code.

    Allows you to run an async function in non-async code, even if there is an
    active event loop. WILL BLOCK.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        print("No running loop")
        return asyncio.run(async_func(*args, **kwargs))

    print("Found running loop")
    print(
        f"Running function '{async_func.__name__}' with args {args} and kwargs {kwargs}"
    )
    return asyncio.run_coroutine_threadsafe(async_func(*args, **kwargs), loop).result()
