import streamlit as st
import streamlit.components.v1 as stc
from st_aggrid import AgGrid, GridOptionsBuilder

import datetime
import pandas as pd

from treelog.logs import LogEntry, MessageType

# TODO: where do we display the tags for this branch?

log_name = "generate_initial_summaries"
log_metadata = {
    "id": "d322545fa7754d7f86cb8960",
    "num": 11,
    "start": "11-28 17:08:06",
    "end": "11-28 17:10:32",
    "duration": "0d 0h 2m 26s",
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
    .copy-button {
        height: 25px;
        width: 25px;
        text-align: center;
        min-height: 0;
        line-height: 0;
        margin:0;
        border-radius: 0.3rem;
        border: 1px solid rgba(250, 250, 250, 0.2);
        background-color: rgb(19, 23, 32);
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
        padding-top: 0;
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
        with st.container(border=False, height=25):
            st.markdown(f"`{data}`")
    if copiable:
        with button_col:
            copy_button(data)


st.title("Logs")
col_1, col_2 = st.columns([0.6, 0.4], vertical_alignment="top")
with col_1:
    with st.container(border=True):
        data_row("Current Log:", log_name)
    with st.container(border=True):
        data_row("Log ID:", log_metadata["id"])
        data_row("Num entries:", log_metadata["num"], copiable=False)
        data_row("Duration", log_metadata["duration"], copiable=False)
        data_row("Start:", log_metadata["start"])
        data_row("End:", log_metadata["end"])
with col_2:
    with st.container(border=True):
        st.write("Parent:")
        st.button("`Parent`", use_container_width=True, key="parent-button")
    with st.container(border=True):
        st.write("Children:")
        with st.container(border=False, height=88):
            for i in range(10):
                st.button(
                    f"`Button {i}`", use_container_width=True, key=f"child-button-{i}"
                )


def render_log_row(row: LogEntry):
    time = datetime.datetime.fromtimestamp(row.timestamp)
    time_col, message_type_col, message_col, metadata_col = st.columns(
        [0.1, 0.1, 0.7, 0.1]
    )
    with time_col:
        st.markdown(f"`{time}`")


with st.container():
    for entry in logs:
        render_log_row(entry)


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
