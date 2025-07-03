try:
    from bramble.ui.bramble_ui import cli
except ImportError:

    class _UIError:
        def __call__(self, *args, **kwds):
            raise ImportError(
                "To use the bramble UI, please install the ui extras. (e.g. `pip install bramble[ui]`)"
            )

        def __getattribute__(self, *args, **kwds):
            raise ImportError(
                "To use the bramble UI, please install the ui extras. (e.g. `pip install bramble[ui]`)"
            )

    cli = _UIError()
