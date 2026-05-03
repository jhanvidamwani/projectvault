"""Cached CSS loader — reads main.css once per process instead of every script rerun."""
from __future__ import annotations
import os
import streamlit as st


@st.cache_data(show_spinner=False)
def _read_css_file(css_path: str, _mtime: float) -> str:
    """Read CSS file. The mtime parameter invalidates cache when file changes."""
    with open(css_path) as f:
        return f.read()


def inject_main_css() -> None:
    """Inject the main app CSS into the page. Cached for speed."""
    css_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "styles", "main.css",
    )
    if not os.path.exists(css_path):
        return
    mtime = os.path.getmtime(css_path)
    css = _read_css_file(css_path, mtime)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
