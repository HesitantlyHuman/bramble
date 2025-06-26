!TODO: update this to include documentation on the pip extras


# treelog
Tree based logging for async python.

Normal logging struggles with async or multithreading, since logs will often get mixed up. `treelog` instead groups logs into a tree like structure. This way, any result can be easily broken down into its steps. The tree structure is to isolate different synchronous paths through the async system, so that each log is ordered, and the logic can be easily followed.

Below are examples for how the logging works, and the conventions which should be followed when logging.

## Examples
### Creating a Tree Logger
To create a flow logger, simply provide a `FlowLoggerWriter` of any kind, and a name for the logger. Each logger should have a specific and descriptive name which corresponds to the scope of its logging (usually a single function). The logger instances will then generate their own unique ids, which will be used to identify specific runs of the logged code.

Here is an example of creating a flow logger with a `FileFlowLoggingWriter`:
```python
import powergrader_ai.logging

logging_writer = powergrader_ai.logging.FileFlowLoggingWriter("logs")
flow_logger = powergrader_ai.logging.FlowLogger("base", logging_writer)
```

### Logging a Message
The flow logger simply logs text, with an associated timestamp, messsage type, and optional metadata. The metadata is not used by the logger itself, and is purely for the user to add additional context to the log.

To log a message, you simply call the `log` method on the flow logger. Below is an example of how to log a message:

```python
import powergrader_ai.logging

logging_writer = powergrader_ai.logging.FileFlowLoggingWriter("logs")
flow_logger = powergrader_ai.logging.FlowLogger("base", logging_writer)

async def some_async_function(flow_logger: powergrader_ai.logging.FlowLogger):
    await flow_logger.log("This is a log message", message_type=powergrader_ai.logging.MessageType.USER, metadata={"some": "metadata"})
```

### Forking a Flow Logger

The critical functionality of the flow logger is the ability to fork the logger into a new logger. This is done by calling the `fork` method on the flow logger and providing a name for the new flow logger object. This will create a new logger object with a parent-child relationship to the original logger.

Forking should be done whenever entering a new context, to maintain readability of the logs. More specific guildelines can be found below in the [best practices](#best-practices) section, but generally, a fork should be done whenever calling a new function.

Here is an example of forking a flow logger:

```python
import powergrader_ai.logging

logging_writer = powergrader_ai.logging.FileFlowLoggingWriter("logs")
flow_logger = powergrader_ai.logging.FlowLogger("base", logging_writer)

async def async_function_b(flow_logger: powergrader_ai.logging.FlowLogger):
    await flow_logger.log("This is within function b", message_type=powergrader_ai.logging.MessageType.USER, metadata={"some": "metadata"})

async def async_function_a(flow_logger: powergrader_ai.logging.FlowLogger):
    await flow_logger.log("This is within function a", message_type=powergrader_ai.logging.MessageType.USER, metadata={"some": "metadata"})
    await async_function_b(await flow_logger.fork("async_function_b"))
```

After running this code, you will find that there are two traces generated, one for each function. In the parent trace, you will also find an automatic `SYSTEM` message which indicates when the fork occurred.


### Convenience Decorators
To make logging easier, there are three convenience decorators provided. One will log any uncaught exceptions (`@flow_log_exceptions`), one will log the arguments and return value of a function (`@flow_log_function_arguments_and_returns`), and the final does both (`@flow_log`). Unless you have a specific circumstance, it is recommended to use the last decorator for every function you are logging.

Keep in mind that the decorators are designed to be used with async functions, and will not work with synchronous functions.

```python
import powergrader_ai.logging

logging_writer = powergrader_ai.logging.FileFlowLoggingWriter("logs")
flow_logger = powergrader_ai.logging.FlowLogger("base", logging_writer)

@powergrader_ai.logging.flow_log
async def some_async_function(flow_logger: powergrader_ai.logging.FlowLogger):
    await flow_logger.log("This is a log message", message_type=powergrader_ai.logging.MessageType.USER, metadata={"some": "metadata"})
```

## Best Practices
### Message Types
The flow logger has 3 message types: `SYSTEM`, `USER`, and `ERROR`. Each message type is used to indicate a different kind of log message, and should be used in accordance with the following guidelines:

- SYSTEM
    - Indicating when a fork has occurred (handled internally by the logger)
    - Indicating the function arguments of a called function (handled by either the user or the `@flow_log` decorator)
    - Indicating the return value of a called function (handled by either the user or the `@flow_log` decorator)
- ERROR
    - Indicating an error which occurred during the function call (handled by the user or the `@flow_log` decorator)
- USER
    - Logging potentially error-prone modifications/transformations of variables
    - Logging calls to external services and the parameters of those calls (like OpenAI)
    - Logging the results of external services and the parameters of those results (like OpenAI)
    - Logging important control flow

### Forking
Forking should be done whenever entering a new context, as mentioned above. Follow the following guildelines for forking:
- Fork whenever calling a new function
- Fork whenever the execution path becomes asynchronous

As a general guideline, do not have a logger associated with an object or class, instead log on the function level.

### Logging Guidelines
When logging, the following guidelines will help you know if you have logged sufficiently:
- Are you able to run the logged function and reproduce the function call based on the information in the log? This includes any special state which is not included in the function arguments.
- Are you able to locate and understand the final output of the function being logged?
- Do you have enough context to locate where an error occurred if execution stops early?
- Are you able to understand and replicate every external service call, including the settings of the call?
- Are you able to see every transformation of important application data?