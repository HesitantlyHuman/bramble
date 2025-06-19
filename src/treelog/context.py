import contextvars

CURRENT_TREE_LOGGER = contextvars.ContextVar("current_tree_logger", default=None)
