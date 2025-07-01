import streamlit as st

if not "current_branch_id" in st.session_state:
    st.session_state.current_branch_id = None


def go_to_branch(branch_id: str):
    st.session_state.current_branch_id = branch_id


def go_to_search():
    st.session_state.current_branch_id = None
