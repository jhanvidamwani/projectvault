import os
import html as _html
import re
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Archive",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth
from utils.sidebar import render_sidebar
from utils.formatting import relative_time
from services import db_service as db

_clean = lambda t: re.sub(r'<[^>]+>', '', _html.unescape(str(t or ''))).strip()

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""<style>
.arch-card {
    background: #FFFFFF; border: 1px solid rgba(142,94,78,0.18);
    border-radius: 16px; padding: 1rem 1.25rem; margin-bottom: 0.55rem;
    box-shadow: 0 2px 8px rgba(142,94,78,0.07);
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
}
.arch-title { font-size: 0.92rem; font-weight: 600; color: #2C1810; margin-bottom: 0.2rem; }
.arch-meta  { font-size: 0.75rem; color: #A88F87; }
.arch-tags  { display: flex; gap: 0.3rem; flex-wrap: wrap; margin-top: 0.35rem; }
.arch-tag   { font-size: 0.58rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
              color: #8E5E4E; background: #FFE4D8; border: 1px solid rgba(224,112,96,0.25);
              border-radius: 999px; padding: 1px 8px; }
.arch-score { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.5px; color: #A88F87; flex-shrink: 0; }
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user
all_projects = db.get_projects_for_user(user["id"])
render_sidebar(user, active="archive", projects=all_projects)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:2rem;">
    <h2 style="margin:0 0 0.3rem;font-size:1.75rem;font-weight:700;color:#2C1810;line-height:1.2;">Archive</h2>
    <p style="color:#7A6560;font-size:0.8125rem;margin:0;">Projects you've archived. Restore or permanently archive them here.</p>
</div>
""", unsafe_allow_html=True)

active_projects   = [p for p in all_projects if p.get("status") != "archived"]
archived_projects = [p for p in all_projects if p.get("status") == "archived"]

# ── Archive Active Projects ────────────────────────────────────────────────────
col_act, col_arch = st.columns([1, 1], gap="large")

with col_act:
    st.markdown('<div class="pv-section-hdr">Active Projects — Move to Archive</div>', unsafe_allow_html=True)
    if not active_projects:
        st.markdown('<p style="color:#A88F87;font-size:0.82rem;">No active projects.</p>', unsafe_allow_html=True)
    for p in active_projects:
        title  = _clean(p.get("title") or "Untitled")
        health = p.get("health_score") or 0
        tags   = p.get("tags") or []
        status = p.get("status", "active")
        updated = relative_time(p.get("updated_at", ""))
        tag_pills = "".join(f'<span class="arch-tag">{_html.escape(_clean(t))}</span>' for t in tags[:3])
        tag_row   = f'<div class="arch-tags">{tag_pills}</div>' if tags else ""

        st.markdown(
            f'<div class="arch-card">'
            f'<div style="flex:1;min-width:0;">'
            f'<div class="arch-title">{_html.escape(title)}</div>'
            f'<div class="arch-meta">{status.capitalize()} · Updated {updated}</div>'
            f'{tag_row}'
            f'</div>'
            f'<div class="arch-score">{health}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Open", key=f"arch_open_{p['id']}", use_container_width=True):
                st.session_state["current_project"] = p["id"]
                st.switch_page("pages/3_project.py")
        with c2:
            if st.button("Archive →", key=f"arch_do_{p['id']}", use_container_width=True):
                db.update_project(p["id"], {"status": "archived"})
                st.toast(f"'{title}' archived")
                st.rerun()

with col_arch:
    st.markdown('<div class="pv-section-hdr">Archived Projects</div>', unsafe_allow_html=True)
    if not archived_projects:
        st.markdown(
            '<div style="text-align:center;padding:3rem 1rem;">'
            '<div style="font-size:2rem;margin-bottom:0.5rem;">⊡</div>'
            '<p style="color:#A88F87;font-size:0.82rem;">Nothing archived yet.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    for p in archived_projects:
        title   = _clean(p.get("title") or "Untitled")
        health  = p.get("health_score") or 0
        tags    = p.get("tags") or []
        updated = relative_time(p.get("updated_at", ""))
        tag_pills = "".join(f'<span class="arch-tag">{_html.escape(_clean(t))}</span>' for t in tags[:3])
        tag_row   = f'<div class="arch-tags">{tag_pills}</div>' if tags else ""

        st.markdown(
            f'<div class="arch-card" style="opacity:0.8;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div class="arch-title" style="color:#6B4A3E;">{_html.escape(title)}</div>'
            f'<div class="arch-meta">Archived · Last updated {updated}</div>'
            f'{tag_row}'
            f'</div>'
            f'<div class="arch-score">{health}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Restore", key=f"arch_restore_{p['id']}", use_container_width=True, type="primary"):
                db.update_project(p["id"], {"status": "active"})
                st.toast(f"'{title}' restored to active")
                st.rerun()
        with c2:
            if st.button("Delete", key=f"arch_del_{p['id']}", use_container_width=True):
                if st.session_state.get(f"confirm_del_{p['id']}"):
                    db.delete_project(p["id"])
                    st.toast(f"'{title}' permanently deleted")
                    st.session_state.pop(f"confirm_del_{p['id']}", None)
                    st.rerun()
                else:
                    st.session_state[f"confirm_del_{p['id']}"] = True
                    st.toast("Click Delete again to confirm permanent deletion")
