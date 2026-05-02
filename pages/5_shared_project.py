import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Shared Project",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import get_project_by_share_token, get_updates

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown('<div class="pv-brand" style="text-align:center; padding:0.5rem 0;">ProjectVault</div>', unsafe_allow_html=True)
st.divider()

# Share token comes via query params
params = st.query_params
share_token = params.get("token", "")

if not share_token:
    st.error("No share token provided.")
    st.stop()

project = get_project_by_share_token(share_token)
if not project:
    st.error("Project not found or share link is invalid.")
    st.stop()

st.markdown(f"## {project['title']}")
st.markdown(f"<span style='color:#7A6560'>{project.get('description') or ''}</span>", unsafe_allow_html=True)

st.divider()
st.markdown("### Recent Activity")

import html as _html
import re
_clean = lambda t: re.sub(r'<[^>]+>', '', _html.unescape(str(t or ''))).strip()

updates = get_updates(project["id"], limit=20)
type_labels = {
    "note": ("tag-note", "NOTE"),
    "decision": ("tag-decision", "DECISION"),
    "milestone": ("tag-milestone", "MILESTONE"),
    "blocker": ("tag-blocker", "BLOCKER"),
    "pivot": ("tag-pivot", "PIVOT"),
}

for u in updates:
    utype = u.get("update_type", "note")
    css_cls, label = type_labels.get(utype, ("tag-note", "NOTE"))
    date_str = u["created_at"][:10]
    _raw = _clean(u.get("content", ""))
    if len(_raw) > 300:
        _raw = _raw[:300] + "…"
    content = _html.escape(_raw)
    st.markdown(f"""
    <div class="pv-card">
        <div style="display:flex; justify-content:space-between;">
            <span class="tag {css_cls}">{label}</span>
            <span style="color:#7a8f8a; font-size:0.8rem;">{date_str}</span>
        </div>
        <div style="margin-top:0.5rem; font-size:0.875rem; color:#253245;">{content}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='text-align:center; color:#7A6560; margin-top:2rem; font-size:0.85rem;'>Shared via ProjectVault — read-only view</div>", unsafe_allow_html=True)
