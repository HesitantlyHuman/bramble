# bramble
Tree-based logging for python.

Traditional logging in async python will usually result in confusing, unordered logs. Many different functions and contexts may be logging to the same stream simultaneously, making it difficult to follow execution paths, or determine cause and effect. `bramble` solves this issue by splitting your logs into branches, which are organized in a tree like structure.

This way, you can:
- Follow the logic of your program (async, or otherwise)
- Debug concurrent tasks
- Understand how a final result was composed

## Basic Usage
### Creating a Logger
Getting started logging with `bramble` is as easy as defining a backend, and then creating a `TreeLogger`. It is recommended to use `TreeLogger` as a context manager.

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

When logging, the default `MessageType` is `"USER"`. You may also provide arbitrary metadata that you wish to be associated with your message, in a flat dictionary. Accepted value types are: `str`, `int`, `float`, and `bool`.

### Branching
Branching is `bramble`'s core feature. The ability to split your logs, so that they remain correlated and ordered is what allows `bramble` to untangle complex execution paths. Once again, there is a context-based approach, and manual approach.

#### Context-based Branching (Recommended)
Simply decorate any functions that you wish to be a branch point. Any time these functions are called, `bramble` will automatically create a new branch:

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

Each call to a decorated function will result in a unique log branch, and any existing log branches will receive a short message linking to the called function.

#### Manual Branching
If you find yourself needing to manage things by hand, simply branch any existing `LogBranch` object. Each branch must be provided a name.

```python
tree_logger = bramble.TreeLogger(logging_backend)
root_branch = tree_logger.root
another_branch = root_branch.branch("new branch")
another_branch.log(message="Some message to log")
```

### Metadata
Each of `bramble`'s `LogBranch`s supports arbitrary user metadata and tags. Tags make it easier to find and identify branches, and metadata allows to you attach additional information for easy programmatic access later.

#### Using the `@branch` decorator
The easiest way to add tags and metadata to a branch is using the `@branch` decorator. Either use the `tag` and `metadata` keywords, or just place any number of lists and dictionaries as arguments.

```python
@bramble.branch(tags=["tag one", "tag two"])
@bramble.branch(metadata={"item" : "value", "another": 1.0})
@bramble.branch(["a tag"])
@bramble.branch(["a tag"], {"key", 234, "key 2": 215}, ["b tag", "c tag"], {"key_2": 120}) # Dictionary which come after will update previous arguments
```

#### Using `apply`
If you do not know your tags or metadata before runtime, you can still use tags and metadata with your in-context branches. Simply use the `apply` function to apply tags and metadata to all current branches. The interface for this function is almost identical to that of the decorator.

```python
@bramble.branch
async def my_function()
  ...
  bramble.apply(tags=["tag one", "tag two"])
  bramble.apply(["a tag"], {"key", 234, "key 2": 215}, ["b tag", "c tag"], {"key_2": 120})
```

#### Manual Tagging and Metadata
The final way to add tags or metadata to a branch is to do so directly. If you have a `LogBranch` object, you can simply call `add_tags` or `add_metadata`.

```python
root = my_logger.root
branch = root.branch("my branch")
branch.add_tags(["tag_one", "tag_two"])
branch.add_metadata({"key": 234})
```

### Demo File
For a complete example of `bramble` in use, please refer to
[`demo.py`](demo.py).

## Installing
To install with pip
```shell
pip install bramble
```

#### Extras
If you want to use `bramble`'s Streamlit UI to view the logs that you
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
simple Streamlit UI which you can use to view the logs. Simply use the command `bramble-ui` to run the UI. Currently, you can choose to point the UI at either a file-based or redis
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
port that you provided, in a browser of your choice.

![Search View Example](docs\search.png)

![Log View Example](docs\logs.png)

## Best Practices
### Message Types
`bramble` currently supports 3 message types: `SYSTEM`, `USER`, and `ERROR`.

**SYSTEM**
- Branch creation (auto-handled)
- Arguments and return values (handled by either the
  user or the `@branch` decorator)

**USER**
- Changes to application state
- External API calls and responses
- Important control flow

**ERROR**
- Exceptions or error conditions (handled by the
  user or the `@branch` decorator)

### Branching
Branching should be done whenever entering a new context, as mentioned above. As a general guideline, do not have a logger associated with an object or class,
instead log on the function level.

## Contributing
If you wish to contribute, please install `bramble` with the `dev` extras. We
use the `black` formatter to ensure consistent code, and attempt to keep a
strict 80 character line limit, where possible.