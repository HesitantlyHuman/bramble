from importlib import resources

import click

# Things that we need to expose through the CLI
# - Streamlit port
# - Choice of backend
#   - Redis
#       - host
#       - port
#   - Files
#       - filepath

# Really only need one command, to start the ui


def run():
    import streamlit.web.cli as stcli
    import sys

    ui_path = resources.files("treelog.ui").joinpath("main.py")

    sys.argv = ["streamlit", "run", ui_path]
    sys.exit(stcli.main())


if __name__ == "__main__":
    run()
