import os
import re
import html as _html
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Team",
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
.team-card {
    background: #FFFFFF; border: 1px solid rgba(142,94,78,0.18);
    border-radius: 16px; padding: 1rem 1.25rem; margin-bottom: 0.55rem;
    box-shadow: 0 2px 8px rgba(142,94,78,0.07);
    display: flex; align-items: center; gap: 0.85rem;
}
.team-avatar {
    width: 38px; height: 38px; border-radius: 50%;
    background: #E07060; display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700; color: #FFFFFF; flex-shrink: 0;
}
.team-name   { font-size: 0.88rem; font-weight: 600; color: #2C1810; }
.team-email  { font-size: 0.75rem; color: #A88F87; }
.team-role   { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
               color: #8E5E4E; background: #FFE4D8; border: 1px solid rgba(224,112,96,0.25);
               border-radius: 999px; padding: 1px 8px; display: inline-block; margin-top: 0.2rem; }
.team-proj-tag {
    font-size: 0.58rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em;
    color: #6B4A3E; background: rgba(142,94,78,0.08); border: 1px solid rgba(142,94,78,0.18);
    border-radius: 6px; padding: 1px 7px; display: inline-block;
}
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user
all_projects = db.get_projects_for_user(user["id"])
render_sidebar(user, active="team", projects=all_projects)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:2rem;">
    <h2 style="margin:0 0 0.3rem;font-size:1.75rem;font-weight:700;color:#2C1810;line-height:1.2;">Team</h2>
    <p style="color:#7A6560;font-size:0.8125rem;margin:0;">All collaborators across your projects.</p>
</div>
""", unsafe_allow_html=True)

# Gather all collaborators across all projects
seen_users: dict[str, dict] = {}   # user_id → {user data + projects list}

for project in all_projects:
    pid    = project["id"]
    ptitle = _clean(project.get("title") or "Untitled")
    collabs = db.get_collaborators(pid)
    for c in collabs:
        uid  = c.get("user_id", "")
        role = c.get("role", "viewer")
        udat = c.get("users") or {}
        if uid not in seen_users:
            seen_users[uid] = {
                "id":       uid,
                "name":     _clean(udat.get("name") or ""),
                "email":    udat.get("email") or "",
                "role":     role,
                "projects": [],
            }
        seen_users[uid]["projects"].append({"title": ptitle, "pid": pid, "role": role})
        # Upgrade role display (owner > editor > viewer)
        if role == "owner":
            seen_users[uid]["role"] = "owner"
        elif role == "editor" and seen_users[uid]["role"] not in ("owner",):
            seen_users[uid]["role"] = "editor"

members = sorted(seen_users.values(), key=lambda m: (
    0 if m["role"] == "owner" else (1 if m["role"] == "editor" else 2),
    m.get("name") or m.get("email") or "",
))

ROLE_COLORS = {
    "owner":  ("#8E5E4E", "#FFE4D8"),
    "editor": ("#6B4A3E", "rgba(142,94,78,0.1)"),
    "viewer": ("#A88F87", "rgba(142,94,78,0.06)"),
}

col_main, col_side = st.columns([3, 2], gap="large")

with col_main:
    st.markdown(
        f'<div class="pv-section-hdr">{len(members)} Member{"s" if len(members) != 1 else ""}</div>',
        unsafe_allow_html=True,
    )
    if not members:
        st.markdown(
            '<div style="text-align:center;padding:4rem 1rem;">'
            '<div style="font-size:2rem;margin-bottom:0.5rem;">◎</div>'
            '<p style="color:#A88F87;font-size:0.82rem;">No collaborators yet. Invite someone via the sidebar.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    for m in members:
        initials  = "".join(n[0].upper() for n in (m["name"] or m["email"] or "?").split()[:2]) or "?"
        name_disp = _html.escape(m["name"] or m["email"] or "Unknown")
        email_disp = _html.escape(m["email"] or "")
        rc, rb = ROLE_COLORS.get(m["role"], ("#A88F87", "rgba(142,94,78,0.06)"))
        proj_tags = "".join(
            f'<span class="team-proj-tag">{_html.escape(p["title"][:18])}</span> '
            for p in m["projects"][:4]
        )
        st.markdown(
            f'<div class="team-card">'
            f'<div class="team-avatar">{initials}</div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div class="team-name">{name_disp}</div>'
            f'<div class="team-email">{email_disp}</div>'
            f'<div style="margin-top:0.35rem;display:flex;flex-wrap:wrap;gap:0.3rem;align-items:center;">'
            f'<span class="team-role" style="color:{rc};background:{rb};">{m["role"].upper()}</span>'
            f'{proj_tags}'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if m["id"] != user["id"]:
            if st.button(f"View projects with {(m['name'] or m['email'] or '')[:16]}", key=f"team_open_{m['id']}", use_container_width=True):
                st.switch_page("pages/2_dashboard.py")

with col_side:
    st.markdown('<div class="pv-section-hdr">Invite to a Project</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);border-radius:14px;padding:1rem 1.25rem;
                font-size:0.82rem;color:#6B4A3E;line-height:1.7;">
        To invite a collaborator to a specific project:<br><br>
        1. Open the project<br>
        2. Go to the <strong>Settings</strong> tab<br>
        3. Use the <strong>Collaborators</strong> section to add by email<br><br>
        Or share a read-only link from the <strong>sidebar → Invite Member</strong>.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="pv-section-hdr">Projects Overview</div>', unsafe_allow_html=True)
    for project in all_projects[:8]:
        ptitle  = _html.escape(_clean(project.get("title") or "Untitled"))
        pstatus = project.get("status", "active")
        health  = project.get("health_score") or 0
        STATUS_CLR = {"active": "#E07060", "paused": "#C4A882", "completed": "#8E5E4E", "archived": "#A88F87"}
        sc = STATUS_CLR.get(pstatus, "#A88F87")
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:0.6rem 0;border-bottom:1px solid rgba(142,94,78,0.08);">'
            f'<div>'
            f'<div style="font-size:0.82rem;font-weight:600;color:#2C1810;">{ptitle}</div>'
            f'<div style="font-size:0.68rem;color:{sc};">{pstatus.capitalize()}</div>'
            f'</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:#A88F87;">{health}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
