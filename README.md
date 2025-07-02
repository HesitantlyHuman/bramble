# treelog
Tree based logging for async python.

Normal logging struggles in async python, since logs will often get mixed up,
and it may not be clear what happened in what order. `treelog` instead groups
logs into a tree like structure. This way, any result can be easily broken down
into its steps. The tree structure is to isolate different synchronous paths
through the async system, so that each log is ordered, and the logic can be
easily followed.

## Basic Usage
### Creating a Logger
Creating a logger is as easy as defining a backend, and then creating a `TreeLogger`. Generally, it is advisable to use `treelog` loggers as context managers.

```python
import treelog
import treelog.backends

logging_backend = treelog.backends.FileWriter("some_folder_path")
with treelog.TreeLogger(logging_backend):
    ...
```

### Logging
Once a logger has been created, you can begin logging. There are two ways to do so: First, if you are in the context of a `TreeLogger`, you can simply log directly.

```python
with treelog.TreeLogger(logging_backend):
    treelog.log(message="Some message to log")
```

If you do not wish to use `TreeLogger` as a context manager, you will instead need to call the logging methods of your `Treelogger`'s branches.

```python
tree_logger = treelog.TreeLogger(logging_backend)
root_branch = tree_logger.root
another_branch = root_branch.branch("new branch")
another_branch.log(message="Some message to log")
```

### Branching
The main feature of `treelog` is the ability to branch logs, so that logs are separate between concurrently running functions. Once again, there is the context approach, and the manual approach.

If you are using a context manager, then you can simply decorate any functions that you wish to be branch points. Any time these functions are called, `treelog` will automatically create a new branch for logging. For example:

```python
@treelog.branch
async def async_fn():
    treelog.log("some log message")
    sync_fn()

@treelog.branch
def sync_fn():
    treelog.log("another log message")

with treelog.TreeLogger(logging_backend):
    asyncio.run(async_fn())
```

In the above example, the logs in each function will be kept separate, even between runs of the same function. While this may not be useful for this toy example, anytime your code includes `asyncio.gather` or similar, it can be invaluable.

The manual branching approach can be easily demonstrated by this previous example:

```python
tree_logger = treelog.TreeLogger(logging_backend)
root_branch = tree_logger.root
another_branch = root_branch.branch("new branch")
another_branch.log(message="Some message to log")
```

Anytime a logger branch is branched, a log entry will be added to parent branch at the appropriate location.

## Installing
To install `treelog`, simply use pip
```shell
pip install treelog
```

However, if you want to use the built-in Streamlit UI to view the logs that you
create, you should install `treelog` with the `ui` extras.
```shell
pip install treelog[ui]
```

Some backends will also require extras, such as redis.
```shell
pip install treelog[redis]
```

## UI
TODO!

## Best Practices
### Message Types
The flow logger has 3 message types: `SYSTEM`, `USER`, and `ERROR`. Each message type is used to indicate a different kind of log message, and should be used in accordance with the following guidelines:

**SYSTEM**
- Indicating when a branch has occurred (handled internally by the logger)
- Indicating the function arguments of a called function (handled by either the user or the `@branch` decorator)
- Indicating the return value of a called function (handled by either the user or the `@branch` decorator)

**ERROR**
- Indicating an error which occurred during the function call (handled by the user or the `@branch` decorator)

**USER**
- Logging potentially error-prone modifications/transformations of variables
- Logging calls to external services and the parameters of those calls
- Logging the results of external services and the parameters of those results
- Logging important control flow

### Branching
Branching should be done whenever entering a new context, as mentioned above. Follow the following guidelines for branching:
- Fork whenever calling a new function
- Fork whenever the execution path becomes asynchronous

As a general guideline, do not have a logger associated with an object or class, instead log on the function level.