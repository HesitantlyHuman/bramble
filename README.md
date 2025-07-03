# bramble
Tree based logging for python.

Normal logging struggles in async python, since logs will often get mixed up,
and it may not be clear what happened in what order. `bramble` instead groups
logs into a tree like structure. This way, any result can be easily broken down
into its steps. The tree structure is to isolate different synchronous paths
through the async system, so that each log is ordered, and the logic can be
easily followed.

## Basic Usage
### Creating a Logger
Creating a logger is as easy as defining a backend, and then creating a
`TreeLogger`. Generally, it is advisable to use `bramble` loggers as context
managers.

```python
import bramble
import bramble.backends

logging_backend = bramble.backends.FileWriter("some_folder_path")
with bramble.TreeLogger(logging_backend):
    ...
```

### Logging
Once a logger has been created, you can begin logging. There are two ways to do
so: First, if you are in the context of a `TreeLogger`, you can simply log
directly.

```python
with bramble.TreeLogger(logging_backend):
    bramble.log(message="Some message to log")
```

If you do not wish to use `TreeLogger` as a context manager, you will instead
need to call the logging methods of your `Treelogger`'s branches.

```python
tree_logger = bramble.TreeLogger(logging_backend)
root_branch = tree_logger.root
another_branch = root_branch.branch("new branch")
another_branch.log(message="Some message to log")
```

### Branching
The main feature of `bramble` is the ability to branch logs, so that logs are
separate between concurrently running functions. Once again, there is the
context approach, and the manual approach.

If you are using a context manager, then you can simply decorate any functions
that you wish to be branch points. Any time these functions are called,
`bramble` will automatically create a new branch for logging. For example:

```python
@bramble.branch
async def async_fn():
    bramble.log("some log message")
    sync_fn()

@bramble.branch
def sync_fn():
    bramble.log("another log message")

with bramble.TreeLogger(logging_backend):
    asyncio.run(async_fn())
```

In the above example, the logs in each function will be kept separate, even
between runs of the same function. While this may not be useful for this toy
example, anytime your code includes `asyncio.gather` or similar, it can be
invaluable.

The manual branching approach can be easily demonstrated by this previous
example:

```python
tree_logger = bramble.TreeLogger(logging_backend)
root_branch = tree_logger.root
another_branch = root_branch.branch("new branch")
another_branch.log(message="Some message to log")
```

Anytime a logger branch is branched, a log entry will be added to parent branch
at the appropriate location.

### Demo File
For a more full example of `bramble` in use, please refer to
[`demo.py`](demo.py).

## Installing
To install `bramble`, simply use pip
```shell
pip install bramble
```

However, if you want to use the built-in Streamlit UI to view the logs that you
create, you should install `bramble` with the `ui` extras.
```shell
pip install bramble[ui]
```

Some backends will also require extras, such as redis.
```shell
pip install bramble[redis]
```

## UI
If you install `bramble` with the `ui` extras, `bramble` provides access to a
simple Streamlit UI which you can use to view the logs. If you have installed
`bramble` with the `ui` extras, simply use the command `bramble-ui` to run the
UI. Currently, you can choose to point the UI at either a file-based or redis
backend.

```
Usage: bramble-ui run [OPTIONS]

  Launch the bramble UI to view logs.

Options:
  --port INTEGER           Port to run the Streamlit app on.
  --backend [redis|files]  Backend to use.  [required]
  --redis-host TEXT        Redis host (if using redis backend).
  --redis-port INTEGER     Redis port (if using redis backend).
  --filepath PATH          Path to log file (if using files backend).
  --help                   Show this message and exit.
```

Once you have launched the UI, you can access it on your local machine via the
port that you provided, in a browser of your choice, where you will see the
search screen. This screen will allow you to select from any branch that was
saved to the currently running backend.

![Search View Example](docs\search.png)

From there, you can open any branch that you wish to view, and you will enter
the logs screen. This screen allows you to navigate the tree of the branch you
selected, as well as return to the search screen.

![Log View Example](docs\logs.png)

## Best Practices
### Message Types
The flow logger has 3 message types: `SYSTEM`, `USER`, and `ERROR`. Each message
type is used to indicate a different kind of log message, and should be used in
accordance with the following guidelines:

**SYSTEM**
- Indicating when a branch has occurred (handled internally by the logger)
- Indicating the function arguments of a called function (handled by either the
  user or the `@branch` decorator)
- Indicating the return value of a called function (handled by either the user
  or the `@branch` decorator)

**ERROR**
- Indicating an error which occurred during the function call (handled by the
  user or the `@branch` decorator)

**USER**
- Logging potentially error-prone modifications/transformations of variables
- Logging calls to external services and the parameters of those calls
- Logging the results of external services and the parameters of those results
- Logging important control flow

### Branching
Branching should be done whenever entering a new context, as mentioned above.
Follow the following guidelines for branching:
- Fork whenever calling a new function
- Fork whenever the execution path becomes asynchronous

As a general guideline, do not have a logger associated with an object or class,
instead log on the function level.


## Contributing
If you wish to contribute, please install `bramble` with the `dev` extras. We
use the `black` formatter to ensure consistent code, and attempt to keep a
strict 80 character line limit, where possible.