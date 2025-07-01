import streamlit as st

from treelog.ui.logs import run_logs
from treelog.ui.search import run_search
from treelog.ui.styles import style

if __name__ == "__main__":
    style()
    if st.session_state.current_branch_id is None:
        run_search()
    else:
        run_logs()
