import streamlit as st
import streamlit.components.v1 as stc
from st_aggrid import AgGrid, GridOptionsBuilder

import datetime
import pandas as pd

from treelog.logs import LogEntry, MessageType


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
}
logs = [
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
df = pd.DataFrame(logs)

st.set_page_config(page_title="Page Title", layout="wide")

st.markdown(
    """
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stAppDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""",
    unsafe_allow_html=True,
)

style = """
<style>
    .st-key-log-view {
        max-height: 96vh;
        display: grid;
        grid-template-rows: auto auto 1fr;
    }

    .st-key-log-view > :last-child {
        overflow: auto;
    }

    .st-key-header {
        display: flex;
        flex-direction: row;
    }

    .st-key-back-button{
        width: 15rem;
        display: flex;
        justify-content: flex-end;
        flex-direction: column;
    }

    [class*="st-key-log-row"] {
        border-top: 1px solid rgba(250, 250, 250, 0.2);
        padding-top: 1rem;
        padding-bottom: 0.5rem;
    }

    .st-key-logs-container {
        gap: 0;
    }

    .pill {
        border: 1px solid;
        border-radius: 999px;
        padding-block: 0.25rem;
        padding-inline: 1rem;
        font-size: medium;
        font-family: monospace;
    }

    .user {
        color: rgb(61, 213, 109);
        border-color: rgb(61, 213, 109);
        background-color: #011004;
    }

    .error {
        color: rgb(255, 75, 75);
        border-color: rgb(255, 75, 75);
        background-color: #160202;
    }

    .system {
        color: oklch(70.7% 0.165 254.624);
        border-color: oklch(70.7% 0.165 254.624);
        background-color: #020a16;
    }

    .message {
        font-family: monospace;
        margin-bottom: 1rem;
    }

    .pilcrow {
        color: rgba(250, 250, 250, 0.35);
    }

    .copy-button {
        height: 25px;
        width: 25px;
        text-align: center;
        min-height: 0;
        line-height: 0;
        margin:0;
        border-radius: 1rem;
        border: 1px solid rgba(250, 250, 250, 0.2);
        background-color: rgb(19, 23, 32);
        font-size: small;
    }

    .copy-button:hover {
        border-color: rgb(255, 75, 75);
    }

    .copy-button:active {
        background: rgb(255, 75, 75);;
    }

    [class*="st-key-child-button"] button {
        height: 30px;
        min-height: 0;
    }

    .st-key-parent-button button {
        height: 30px;
        min-height: 0;
    }

    .copy-button {
        width: 25px !important;
        height: 25px !important;
        padding: 0 !important;
        min-height: 0 !important;
        border-radius: 0.3rem !important;
        text-align: center;
    }

    .st-emotion-cache-gsx7k2 {
        gap: 0.5rem;
    }

    .st-emotion-cache-ajtf3x {
        gap: 0.5rem;
    }

    .stAppHeader {
        display: none;
    }

    .stMainBlockContainer {
        padding-block: 0;
        max-width: 100rem;
    }
</style>
"""
st.write(style, unsafe_allow_html=True)

copy_id = 0


def copy_button(text_to_copy: str):
    global copy_id
    st.markdown(
        f"""<button class="copy-button" id="st-key-copy-button-{copy_id}" data="{text_to_copy}">⧉</button>""",
        unsafe_allow_html=True,
    )
    copy_id += 1


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


with st.container(key="log-view"):
    with st.container(key="header"):
        st.markdown("## Log View")
        st.button("<- Back to Search", key="back-button", use_container_width=True)
    col_1, col_2 = st.columns([0.6, 0.4], vertical_alignment="top")
    with col_1:
        with st.container(border=True):
            data_row("Current Log:", log_name)
        with st.container(border=True):
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
            st.button("`Parent`", use_container_width=True, key="parent-button")
        with st.container(border=True):
            st.write("Children:")
            with st.container(border=False, height=160):
                for i in range(5):
                    st.button(
                        f"`Button {i}`",
                        use_container_width=True,
                        key=f"child-button-{i}",
                    )

    log_row = 0

    def get_type_pill(type):
        match type.value:
            case "user":
                return "<span class='pill user'>USER</span>"
            case "system":
                return "<span class='pill system'>SYSTEM</span>"
            case "error":
                return "<span class='pill error'>ERROR</span>"

    def render_log_row(row: LogEntry):
        global log_row
        with st.container(key=f"log-row-{log_row}"):
            time = datetime.datetime.fromtimestamp(row.timestamp)
            time_col, message_type_col, message_col, metadata_col = st.columns(
                [0.18, 0.08, 0.59, 0.15]
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
        for entry in logs:
            render_log_row(entry)


# TODO:
# - figure out how to keep the log column headers in place
# - Pin the log view metadata and controls (maybe just see if the logs can scroll)
# - Figure out how to dynamically update the log content for searching or ordering
# - Test that the metadata viewing works well for larger metadata
# - Figure out where and how to display the tags and metadata for the branch itself (Maybe we should just use the json thing for that? for all of the data?)
# - Put in some real test data so that we can actually see how it is working
# - Figure out how to make a nice button for the branch linking in messages
# - Figure out how to add copying to the log messages and their timestamps

copy_buttons_script = """
    <script>
        const parentDOM = window.parent.document;

        const buttons = parentDOM.getElementsByClassName("copy-button");
        console.log(buttons);
        for (let button of buttons) {
            button.addEventListener("click", () => {
                const data = button.getAttribute("data");
                navigator.clipboard.writeText(data).then(() => {
                    console.log("Copied:", data);
                    button.innerText = "✓";
                    setTimeout(() => button.innerText = "⧉", 1000);
                }).catch(err => {
                    console.error("Copy failed:", err);
                });
            })
        }
    </script>
"""
stc.html(copy_buttons_script, height=0)
