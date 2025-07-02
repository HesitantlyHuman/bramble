try:
    from lumberjack.ui.treelog_ui import cli
except ImportError:

    class _UIError:
        def __call__(self, *args, **kwds):
            raise ImportError(
                "To use the lumberjack UI, please install the ui extras. (e.g. `pip install lumberjack[ui]`)"
            )

        def __getattribute__(self, *args, **kwds):
            raise ImportError(
                "To use the lumberjack UI, please install the ui extras. (e.g. `pip install lumberjack[ui]`)"
            )

    cli = _UIError()
