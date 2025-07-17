import sys
from importlib import resources
import click

import streamlit
import streamlit.web.cli as stcli


@click.group()
def cli():
    """CLI for bramble-ui — a UI for viewing bramble logs."""
    pass


@cli.command()
@click.option(
    "--port", type=int, default=8501, help="Port to run the Streamlit app on."
)
@click.option(
    "--backend",
    type=click.Choice(["redis", "files"]),
    required=True,
    help="Backend to use.",
)
@click.option(
    "--redis-host",
    default="127.0.0.1",
    help="Redis host (if using redis backend).",
)
@click.option(
    "--redis-port",
    type=int,
    default=6379,
    help="Redis port (if using redis backend).",
)
@click.option(
    "--filepath",
    type=click.Path(exists=True),
    help="Path to log file (if using files backend).",
)
def run(port, backend, redis_host, redis_port, filepath):
    """
    Launch the bramble UI to view logs.
    """

    # Determine backend arguments
    backend_args = []
    if backend == "redis":
        backend_args.extend(
            [
                "--backend",
                "redis",
                "--redis-host",
                redis_host,
                "--redis-port",
                str(redis_port),
            ]
        )
    elif backend == "files":
        if not filepath:
            click.echo(
                "Error: --filepath is required when using the 'files' backend.",
                err=True,
            )
            sys.exit(1)
        backend_args.extend(["--backend", "files", "--filepath", filepath])

    # Get the Streamlit entrypoint
    ui_path = resources.files("bramble.ui").joinpath("main.py")

    # Construct the final argv for streamlit
    sys.argv = [
        "streamlit",
        "run",
        str(ui_path),
        "--server.port",
        str(port),
        "--",
    ] + backend_args

    # Run streamlit

    sys.exit(stcli.main())


if __name__ == "__main__":
    cli()
