from treelog.logger import TreeLogger
from treelog.logs import MessageType


def tree_log_exceptions(func):
    async def wrapper(*args, **kwargs):
        # First, find if there are any tree loggers in the arguments
        # or keyword arguments
        tree_loggers = [arg for arg in args if isinstance(arg, TreeLogger)] + [
            kwarg for kwarg in kwargs.values() if isinstance(kwarg, TreeLogger)
        ]
        # If there are no tree loggers, just run the function
        if not tree_loggers:
            return await func(*args, **kwargs)
        # Otherwise, run the function and log any exceptions
        else:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                for logger in tree_loggers:
                    await logger.log(str(e), MessageType.ERROR)
                raise e

    return wrapper


def tree_log_function_arguments_and_returns(func):
    async def wrapper(*args, **kwargs):
        # First, find if there are any tree loggers in the arguments
        # or keyword arguments
        tree_loggers = [arg for arg in args if isinstance(arg, TreeLogger)] + [
            kwarg for kwarg in kwargs.values() if isinstance(kwarg, TreeLogger)
        ]
        # If there are no tree loggers, just run the function
        if not tree_loggers:
            return await func(*args, **kwargs)
        # Otherwise, run the function and log the arguments and returns
        else:
            # Now format the args and kwargs like they are a function call
            function_call = f"{func.__name__}("
            for arg in args:
                function_call += f"{arg},\n"
            for key, value in kwargs.items():
                function_call += f"{key}={value},\n"
            function_call += ")"

            for logger in tree_loggers:
                await logger.log(f"Function call: {function_call}", MessageType.SYSTEM)

            result = await func(*args, **kwargs)

            for logger in tree_loggers:
                await logger.log(f"Function return: {result}", MessageType.SYSTEM)

            return result

    return wrapper


def tree_log(func):
    return tree_log_exceptions(tree_log_function_arguments_and_returns(func))
