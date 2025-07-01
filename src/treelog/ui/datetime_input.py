import datetime

import streamlit as st

datetime_id = 0


def datetime_input():
    global datetime_id

    col_1, col_2 = st.columns(2)
    with col_1:
        date = st.date_input(
            label="Date",
            value=None,
            label_visibility="collapsed",
            key=f"datetime-input-date-{datetime_id}",
        )
    with col_2:
        sub_col_1, sub_col_2, sub_col_3 = st.columns(3)
        with sub_col_1:
            hours = st.selectbox(
                label="Hours",
                index=None,
                options=[i for i in range(24)],
                placeholder="HH",
                label_visibility="collapsed",
                key=f"datetime-input-hours-{datetime_id}",
            )
        with sub_col_2:
            minutes = st.selectbox(
                label="Minutes",
                index=None,
                options=[i for i in range(60)],
                placeholder="mm",
                label_visibility="collapsed",
                key=f"datetime-input-minutes-{datetime_id}",
            )
        with sub_col_3:
            seconds = st.selectbox(
                label="Seconds",
                index=None,
                options=[i for i in range(60)],
                placeholder="ss",
                label_visibility="collapsed",
                key=f"datetime-input-seconds-{datetime_id}",
            )

    datetime_id += 1

    if date is None:
        return None

    if hours is None:
        hours = 0

    if minutes is None:
        minutes = 0

    if seconds is None:
        seconds = 0

    return datetime.datetime(date.year, date.month, date.day, hours, minutes, seconds)
