try:
    from treelog.ui.run import run
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

    run = _UIError()
