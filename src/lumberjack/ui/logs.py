from typing import List, Dict, Any

import streamlit as st

import datetime

from lumberjack.logs import LogEntry
from lumberjack.ui.copy_button import copy_button, enable_copy_buttons
from lumberjack.ui.navigation import go_to_branch, go_to_search
from lumberjack.ui.data import load_branch_data

# TODO: improve rendering of parent and children to use the names of the branches instead of the ids


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
                            on_click=lambda child_id=child_id: go_to_branch(child_id),
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

            has_branch = (
                row.entry_metadata is not None and "branch_id" in row.entry_metadata
            )

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
                    if not has_branch:
                        text = row.message.replace(
                            "\n", '<span class="pilcrow">¶</span>\n'
                        )
                        lines = text.split("\n")
                        lines = "<br>".join(lines)
                        st.markdown(
                            f'<div class="message">{lines}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.button(
                            label=row.message,
                            on_click=lambda: go_to_branch(
                                row.entry_metadata["branch_id"]
                            ),
                            key=f"branch-button-{log_row}",
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
    from lumberjack.ui.styles import style

    style()
    run_logs()
