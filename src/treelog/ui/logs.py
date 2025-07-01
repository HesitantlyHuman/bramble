from typing import List, Dict, Any

import streamlit as st

import datetime

from treelog.logs import LogEntry, MessageType
from treelog.ui.copy_button import copy_button, enable_copy_buttons
from treelog.ui.navigation import go_to_branch, go_to_search


@st.cache_data
def load_branch_data(id: str):
    log_name = "generate_initial_summaries"
    log_metadata = {
        "id": "d322545fa7754d7f86cb8960",
        "num": 11,
        "start": "11-28 17:08:06",
        "end": "11-28 17:10:32",
        "duration": "0d 0h 2m 26s",
        "tags": [
            "a",
            "b",
            "a tag",
            "a larger tag",
            "some-very-weildy-super-long-annoying-tag-that-sucks",
        ],
        "metadata": None,
        "parent": "some id",
        "children": ["some child", "another child", "and then another"],
    }
    log_entries = [
        LogEntry(
            message="entry number 1",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.USER,
            entry_metadata=None,
        ),
        LogEntry(
            message="entry number 2",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.USER,
            entry_metadata=None,
        ),
        LogEntry(
            message="a fun system message",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.SYSTEM,
            entry_metadata=None,
        ),
        LogEntry(
            message="Oh no, an error!",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.ERROR,
            entry_metadata=None,
        ),
        LogEntry(
            message="with metadata",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.USER,
            entry_metadata={"some key": 1253, "another": "this value"},
        ),
        LogEntry(
            message="this is a multiline entry\nyay another line!",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.USER,
            entry_metadata=None,
        ),
        LogEntry(
            message="what about when the line is long enough that it ends up hitting the edge of the message column and may need to wrap? does it wrap correctly? or do we need to scroll?",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.SYSTEM,
            entry_metadata=None,
        ),
        LogEntry(
            message="[USER]: I will now provide you with a rubric. The rubric is comprised of criteria, where each criteria has multiple levels of student achievement. Generate a wholistic description of each of the rubric categories from these level descriptions. (Each category should have a description, not each level. The descriptions should not reference the levels whatsoever) Each category should be distinct from each other category. No categories should overlap.[]",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.USER,
            entry_metadata=None,
        ),
        LogEntry(
            message="[USER]: Criterion Name: Usability\n\n1: The API is highly usable and intuitive. Parameters are consistent between endpoints, and the help endpoint is informative.\n\n2: The API may be slightly unintuitive at times. Name are consistent between endpoints, but the help endpoint may be...",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.USER,
            entry_metadata=None,
        ),
        LogEntry(
            message="[USER]: I will now provide you with a rubric. The rubric is comprised of criteria, where each criteria has multiple levels of student achievement. Generate a wholistic description of each of the rubric categories from these level descriptions. (Each category should have a description, not each level. The descriptions should not reference the levels whatsoever) Each category should be distinct from each other category. No categories should overlap.[]",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.USER,
            entry_metadata=None,
        ),
        LogEntry(
            message="[USER]: Criterion Name: Usability\n\n1: The API is highly usable and intuitive. Parameters are consistent between endpoints, and the help endpoint is informative.\n\n2: The API may be slightly unintuitive at times. Name are consistent between endpoints, but the help endpoint may be...",
            timestamp=datetime.datetime.now().timestamp(),
            message_type=MessageType.USER,
            entry_metadata=None,
        ),
    ]
    from dataclasses import asdict

    return log_name, log_metadata, [asdict(entry) for entry in log_entries]


def data_row(label: str, data: str, copiable: bool = True):
    label_col, data_col, button_col = st.columns([0.25, 0.66, 0.07])
    with label_col:
        with st.container(border=False, height=25):
            st.write(label)
    with data_col:
        if isinstance(data, str):
            with st.container(border=False, height=25):
                st.markdown(f"`{data}`")
        elif isinstance(data, (list, dict)):
            with st.container(border=False):
                st.json(data, expanded=False)
        else:
            with st.container(border=False):
                st.write(data)

    if copiable:
        with button_col:
            copy_button(data)


def render_logs(
    log_name: str, log_metadata: Dict[str, Any], log_entries: List[LogEntry]
):
    with st.container(key="log-view"):
        with st.container(key="header"):
            st.markdown("## Log View")
            with st.container(key="nav-buttons"):
                st.button(
                    "<- Back to Search", use_container_width=True, on_click=go_to_search
                )
        col_1, col_2 = st.columns([0.6, 0.4], vertical_alignment="top")
        with col_1:
            with st.container(border=True):
                data_row("Current Log:", log_name)
            with st.container(border=True, height=264):
                data_row("Log ID:", log_metadata["id"])
                data_row("Num entries:", log_metadata["num"])
                data_row("Duration", log_metadata["duration"])
                data_row("Start:", log_metadata["start"])
                data_row("End:", log_metadata["end"])
                data_row("Tags:", log_metadata["tags"])
                data_row("Metadata:", log_metadata["metadata"])
        with col_2:
            with st.container(border=True):
                st.write("Parent:")
                st.button(
                    f"`{log_metadata['parent']}`",
                    use_container_width=True,
                    key="parent-button",
                    on_click=lambda: go_to_branch(log_metadata["parent"]),
                )
            with st.container(border=True):
                st.write("Children:")
                with st.container(border=False, height=162):
                    for idx, child_id in enumerate(log_metadata["children"]):
                        st.button(
                            f"`{child_id}`",
                            use_container_width=True,
                            key=f"child-button-{idx}",
                            on_click=lambda: go_to_branch(child_id),
                        )

        def get_type_pill(type):
            match type.value:
                case "user":
                    return "<span class='pill user'>USER</span>"
                case "system":
                    return "<span class='pill system'>SYSTEM</span>"
                case "error":
                    return "<span class='pill error'>ERROR</span>"

        LOG_COLUMN_SIZES = [0.16, 0.07, 0.62, 0.15]

        log_row = 0

        def render_log_row(row: LogEntry):
            nonlocal log_row

            if log_row == 0:
                key = "log-row"
            else:
                key = f"log-row-{log_row}"
            with st.container(key=key):
                time = datetime.datetime.fromtimestamp(row.timestamp)
                time_col, message_type_col, message_col, metadata_col = st.columns(
                    LOG_COLUMN_SIZES
                )
                with time_col:
                    st.markdown(f"`{time}`")

                with message_type_col:
                    st.markdown(get_type_pill(row.message_type), unsafe_allow_html=True)

                with message_col:
                    text = row.message.replace("\n", '<span class="pilcrow">¶</span>\n')
                    lines = text.split("\n")
                    lines = "<br>".join(lines)
                    st.markdown(
                        f'<div class="message">{lines}</div>', unsafe_allow_html=True
                    )

                with metadata_col:
                    st.write(row.entry_metadata)

            log_row += 1

        with st.container(border=True, key="logs-container"):
            with st.container(border=False, key="logs-header"):
                time_col, message_type_col, message_col, metadata_col = st.columns(
                    LOG_COLUMN_SIZES
                )
                with time_col:
                    st.write("Time")
                with message_type_col:
                    st.write("Type")
                with message_col:
                    st.write("Message")
                with metadata_col:
                    st.write("Metadata")
            with st.container(border=False, key="logs-entries"):
                for log_entry in log_entries:
                    render_log_row(log_entry)

    enable_copy_buttons()


def run_logs():
    name, meta, entries = load_branch_data(st.session_state.current_branch_id)
    entries = [LogEntry(**entry) for entry in entries]
    render_logs(name, meta, entries)


if __name__ == "__main__":
    from treelog.ui.styles import style

    style()
    run_logs()

# TODO:
# - Figure out how to dynamically update the log content for searching or ordering
# - Put in some real test data so that we can actually see how it is working
# - Figure out how to make a nice button for the branch linking in messages
