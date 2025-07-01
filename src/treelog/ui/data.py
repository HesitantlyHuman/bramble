import streamlit as st
import pandas as pd
import datetime

from treelog.logs import LogEntry, MessageType


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
