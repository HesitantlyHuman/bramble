try:
    from treelog.ui.treelog_ui import cli
except ImportError:

    class _UIError:
        def __call__(self, *args, **kwds):
            raise ImportError(
                "To use the tree logging UI, please install the ui extras. (e.g. `pip install treelog[ui]`)"
            )

        def __getattribute__(self, *args, **kwds):
            raise ImportError(
                "To use the tree logging UI, please install the ui extras. (e.g. `pip install treelog[ui]`)"
            )

    cli = _UIError()
