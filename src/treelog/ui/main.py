import streamlit as st

from treelog.ui.data import start_file_backend
from treelog.ui.logs import run_logs
from treelog.ui.search import run_search
from treelog.ui.styles import style

if __name__ == "__main__":
    # First, we need to start the backend
    start_file_backend("test")

    if not "current_branch_id" in st.session_state:
        st.session_state.current_branch_id = None
    style()
    if st.session_state.current_branch_id is None:
        run_search()
    else:
        run_logs()
