import streamlit as st
import argparse
import sys


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend")
    parser.add_argument("--filepath")
    parser.add_argument("--redis-host")
    parser.add_argument("--redis-port")
    return parser.parse_args(args)


if __name__ == "__main__":
    # First, parse the args
    args = parse_args(sys.argv[1:])

    from bramble.ui.data import start_file_backend, start_redis_backend

    # Then, we need to start the backend
    if args.backend == "files":
        start_file_backend(path=args.filepath)
    elif args.backend == "redis":
        start_redis_backend(host=args.redis_host, port=args.redis_port)
    else:
        raise ValueError(f"Backend type `{args.backend}` is not supported!")

    from bramble.ui.search import run_search
    from bramble.ui.logs import run_logs
    from bramble.ui.styles import style

    if not "current_branch_id" in st.session_state:
        st.session_state.current_branch_id = None
    style()
    if st.session_state.current_branch_id is None:
        run_search()
    else:
        run_logs()
