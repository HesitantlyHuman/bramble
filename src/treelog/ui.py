import streamlit as st

log_name = "generate_initial_summaries"
log_metadata = {
    "id": "129124,124ks09asdj2092jads",
    "num": 11,
    "start": "11-28 17:08:06",
    "end": "11-28 17:10:32",
    "duration": "0d 0h 2m 26s",
}


def copy_button(text_to_copy: str):
    def _copy():
        print(f"copy {text_to_copy}")

    st.button("⧉", on_click=_copy)


st.title("Tree Logs")
with st.container(border=True):
    st.write("Current Log:")
    st.write(log_name)
with st.container(border=True):
    st.write("Log ID:")
    st.write(log_metadata["id"])
    copy_button(log_metadata["id"])
with st.container(border=True):
    st.write("Parent:")
    st.button("Parent")
with st.container(border=True, height=200):
    st.write("Children:")
    for i in range(10):
        st.button(f"Button {i}")
st.dataframe()
