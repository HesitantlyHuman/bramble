from importlib import resources

import streamlit as st


def load_styles() -> str:
    style_path = resources.files("treelog.ui").joinpath("styles.css")
    return style_path.read_text()


def apply_styles(styles: str):
    st.markdown(f"<style>{styles}</styles>", unsafe_allow_html=True)


def style():
    st.set_page_config(page_title="`treelog` Viewer", layout="wide")
    apply_styles(load_styles())
