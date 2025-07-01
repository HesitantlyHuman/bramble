from typing import Dict, List, Any

import streamlit as st

import datetime
import pandas as pd

from treelog.ui.datetime_input import datetime_input
from treelog.ui.navigation import go_to_branch


@st.cache_data
def load_branches_and_tags():
    branches = [
        {
            "name": "some name",
            "id": "24j4k334j9s03fj3",
            "tags": ["a", "b", "c", "give me a tag", "yo, lets get some more tags"],
            "metadata": None,
            "entries": 5,
            "start": datetime.datetime(2025, 5, 20, 5, 32, 12),
            "end": datetime.datetime(2025, 5, 21, 2, 49, 23),
        },
        {
            "name": "some name",
            "id": "2ofilsfeinfeis",
            "tags": ["a", "b"],
            "metadata": {"hey": 124059},
            "entries": 11,
            "start": datetime.datetime(2025, 5, 20, 5, 32, 12),
            "end": datetime.datetime(2025, 5, 21, 2, 59, 23),
        },
        {
            "name": "a differnt name",
            "id": "sfoeik3l3oifsioefj",
            "tags": None,
            "metadata": None,
            "entries": 11,
            "start": datetime.datetime(2025, 6, 20, 21, 3, 12),
            "end": datetime.datetime(2025, 7, 21, 3, 23, 1),
        },
    ]
    branches = pd.DataFrame(branches)
    return branches, ["a", "b", "c", "give me a tag", "yo, lets get some more tags"]


branches, all_tags = load_branches_and_tags()


if not "branch_selected" in st.session_state:
    st.session_state.branch_selected = False

if not "name_filer" in st.session_state:
    st.session_state.name_filter = None

if not "id_filter" in st.session_state:
    st.session_state.id_filter = None

if not "tags_filter" in st.session_state:
    st.session_state.tags_filter = []

if not "datetime_start_filter" in st.session_state:
    st.session_state.datetime_start_filter = None

if not "datetime_end_filter" in st.session_state:
    st.session_state.datetime_end_filter = None


def filter_branches(branches_to_filter):
    filtered = branches_to_filter.copy()

    if st.session_state.name_filter is not None:
        filtered = filtered[
            filtered["name"].apply(lambda x: st.session_state.name_filter in x)
        ]

    if st.session_state.id_filter is not None:
        filtered = filtered[
            filtered["id"].apply(lambda x: st.session_state.id_filter in x)
        ]

    for tag in st.session_state.tags_filter:
        filtered = filtered[
            filtered["tags"].apply(lambda x: False if x is None else tag in x)
        ]

    if st.session_state.datetime_start_filter is not None:
        filtered = filtered[
            filtered["end"].apply(lambda x: x > st.session_state.datetime_start_filter)
        ]

    if st.session_state.datetime_end_filter is not None:
        filtered = filtered[
            filtered["start"].apply(lambda x: x < st.session_state.datetime_end_filter)
        ]

    return filtered


def input_label(label):
    st.markdown(
        f'<span style="padding-inline: 1rem; height: 2.5rem; display: inline-block; align-content: center; font-size: large">{label}:</span>',
        unsafe_allow_html=True,
    )


def render_search(branches: List[Dict[str, Any]], all_tags: List[str]):
    with st.container(key="search-view"):
        with st.container(key="header"):
            st.markdown("## Search")

        # Search options
        OPTIONS_SIZES = [0.15, 0.85]
        with st.container(border=True, key="search-options"):
            # Name
            label_col, input_col = st.columns(OPTIONS_SIZES)
            with label_col:
                input_label("Name")
            with input_col:
                name = st.text_input(
                    label="Name",
                    placeholder="Name to search for",
                    label_visibility="collapsed",
                )
                if not name == "":
                    st.session_state.name_filter = name
                else:
                    st.session_state.name_filter = None

            # ID
            label_col, input_col = st.columns(OPTIONS_SIZES)
            with label_col:
                input_label("ID")
            with input_col:
                branch_id = st.text_input(
                    label="ID",
                    placeholder="ID to search for",
                    label_visibility="collapsed",
                )
                if not branch_id == "":
                    st.session_state.id_filter = branch_id
                else:
                    st.session_state.id_filter = None

            # Tags
            label_col, input_col = st.columns(OPTIONS_SIZES)
            with label_col:
                input_label("Tags")
            with input_col:
                tags = st.multiselect(
                    label="Tags", options=all_tags, label_visibility="collapsed"
                )
                st.session_state.tags_filter = tags

            # Date and Time Start
            label_col, input_col = st.columns(OPTIONS_SIZES)
            with label_col:
                input_label("Start")
            with input_col:
                datetime_output = datetime_input()
                st.session_state.datetime_start_filter = datetime_output

            # Date and Time End
            label_col, input_col = st.columns(OPTIONS_SIZES)
            with label_col:
                input_label("End")
            with input_col:
                datetime_output = datetime_input()
                st.session_state.datetime_end_filter = datetime_output

            st.divider()

            navigation_button = st.empty()

        filtered_branches = filter_branches(branches)

        selection_event = st.dataframe(
            filtered_branches,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
        )
        if len(selection_event["selection"]["rows"]) == 0:
            st.session_state.branch_selected = False
        else:
            st.session_state.branch_selected = True

        def _navigate_to_selection():
            row = selection_event["selection"]["rows"][0]
            branch_id = filtered_branches.iloc[row]["id"]
            go_to_branch(branch_id)

        navigation_button.button(
            "View Selected Branch Logs",
            use_container_width=True,
            disabled=not st.session_state.branch_selected,
            on_click=_navigate_to_selection,
        )


def run_search():
    branches, tags = load_branches_and_tags()
    render_search(branches, tags)


if __name__ == "__main__":
    from treelog.ui.styles import style

    style()
    run_search()
