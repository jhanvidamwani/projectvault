import os
import re
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st


def clean(text):
    if not text:
        return ""
    import html as _h
    t = _h.unescape(str(text))
    t = re.sub(r'<[^>]+>', '', t)
    t = ' '.join(t.split()).strip()
    return "" if "imported from provided" in t.lower() else t

load_dotenv(Path(__file__).parent / ".env", override=True)

# Start weekly digest scheduler once per process
if "scheduler_started" not in st.session_state:
    try:
        from services.email_service import start_scheduler
        start_scheduler()
    except Exception:
        pass
    st.session_state["scheduler_started"] = True

st.set_page_config(
    page_title="ProjectVault",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject global CSS
with open("styles/main.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Route unauthenticated users to login
if "user" not in st.session_state or not st.session_state.get("user"):
    st.switch_page("pages/1_login.py")
else:
    st.switch_page("pages/2_dashboard.py")
