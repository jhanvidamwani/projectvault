import os
import re
import html as _html
from datetime import datetime, timezone
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Schedule",
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
.sched-node {
    display: flex; gap: 1rem; padding: 0.85rem 0;
    border-bottom: 1px solid rgba(142,94,78,0.08);
}
.sched-node:last-child { border-bottom: none; }
.sched-dot-col { display: flex; flex-direction: column; align-items: center; padding-top: 3px; }
.sched-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.sched-line { width: 1.5px; flex: 1; background: rgba(142,94,78,0.12); margin-top: 4px; }
.sched-when { font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 0.15rem; }
.sched-title { font-size: 0.87rem; font-weight: 600; color: #2C1810; }
.sched-proj  { font-size: 0.7rem; color: #A88F87; margin-top: 0.1rem; }
.sched-type  { font-size: 0.58rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
               color: #8E5E4E; background: #FFE4D8; border: 1px solid rgba(224,112,96,0.25);
               border-radius: 999px; padding: 1px 8px; display: inline-block; margin-top: 0.25rem; }
.sched-section-hdr {
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
    color: #2C1810; padding: 0.5rem 0.9rem; background: rgba(224,112,96,0.08);
    border-left: 3px solid #E07060; border-radius: 0 8px 8px 0;
    margin-bottom: 0.5rem; margin-top: 1rem;
}
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user
all_projects = db.get_projects_for_user(user["id"])
render_sidebar(user, active="schedule", projects=all_projects)

project_ids = [p["id"] for p in all_projects]
project_map = {p["id"]: _clean(p.get("title") or "Untitled") for p in all_projects}

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:2rem;">
    <h2 style="margin:0 0 0.3rem;font-size:1.75rem;font-weight:700;color:#2C1810;line-height:1.2;">Schedule</h2>
    <p style="color:#7A6560;font-size:0.8125rem;margin:0;">Milestones, decisions, and key events across all your projects.</p>
</div>
""", unsafe_allow_html=True)

# Fetch all updates and sort chronologically
all_updates = db.get_recent_updates_for_user(project_ids, limit=200) if project_ids else []
milestones  = [u for u in all_updates if u.get("update_type") == "milestone"]
decisions   = [u for u in all_updates if u.get("update_type") == "decision"]
blockers    = [u for u in all_updates if u.get("update_type") == "blocker"]
other       = [u for u in all_updates if u.get("update_type") not in ("milestone","decision","blocker")]

TYPE_CLR = {
    "milestone": "#C4A882",
    "decision":  "#8E5E4E",
    "blocker":   "#CF6F61",
    "note":      "#E07060",
    "pivot":     "#F5C4B4",
}

col_tl, col_stats = st.columns([3, 2], gap="large")

with col_tl:
    # ── Filter ────────────────────────────────────────────────────────
    filter_type = st.selectbox(
        "Show",
        ["All Events", "Milestones only", "Decisions only", "Blockers only"],
        label_visibility="collapsed",
    )
    filter_map = {
        "All Events":      all_updates,
        "Milestones only": milestones,
        "Decisions only":  decisions,
        "Blockers only":   blockers,
    }
    items = filter_map.get(filter_type, all_updates)[:60]

    if not items:
        st.markdown(
            '<div style="text-align:center;padding:4rem 1rem;">'
            '<div style="font-size:2rem;margin-bottom:0.5rem;">◷</div>'
            '<p style="color:#A88F87;font-size:0.82rem;">No events yet. Add updates to your projects to see them here.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        # Group by month
        from collections import defaultdict
        grouped: dict[str, list] = defaultdict(list)
        for item in items:
            ts = item.get("created_at", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                month_key = dt.strftime("%B %Y")
            except Exception:
                month_key = "Unknown"
            grouped[month_key].append(item)

        for month, month_items in grouped.items():
            st.markdown(f'<div class="sched-section-hdr">{_html.escape(month)}</div>', unsafe_allow_html=True)
            nodes_html = ""
            for i, item in enumerate(month_items):
                utype = item.get("update_type", "note")
                clr   = TYPE_CLR.get(utype, "#E07060")
                raw   = _clean(item.get("content") or item.get("ai_summary") or "")
                title = _html.escape(raw[:80] + "…" if len(raw) > 80 else raw)
                proj  = _html.escape(project_map.get(item.get("project_id", ""), ""))
                when  = _html.escape(relative_time(item.get("created_at", "")))
                is_last = i == len(month_items) - 1
                line  = "" if is_last else '<div class="sched-line"></div>'
                nodes_html += (
                    f'<div class="sched-node">'
                    f'<div class="sched-dot-col"><div class="sched-dot" style="background:{clr};"></div>{line}</div>'
                    f'<div>'
                    f'<div class="sched-when" style="color:{clr};">{when}</div>'
                    f'<div class="sched-title">{title}</div>'
                    f'<div class="sched-proj">{proj}</div>'
                    f'<span class="sched-type">{utype.upper()}</span>'
                    f'</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);border-radius:16px;'
                f'padding:0.75rem 1.1rem;margin-bottom:0.75rem;box-shadow:0 2px 8px rgba(142,94,78,0.07);">'
                f'{nodes_html}</div>',
                unsafe_allow_html=True,
            )

with col_stats:
    st.markdown('<div class="pv-section-hdr">At a Glance</div>', unsafe_allow_html=True)
    stats = [
        ("◷", "Total Events",  len(all_updates), "#2C1810"),
        ("●", "Milestones",    len(milestones),  "#C4A882"),
        ("◈", "Decisions",     len(decisions),   "#8E5E4E"),
        ("!", "Blockers",      len(blockers),    "#CF6F61"),
    ]
    for icon, label, count, clr in stats:
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:0.75rem 1rem;background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);'
            f'border-radius:12px;margin-bottom:0.4rem;box-shadow:0 2px 6px rgba(142,94,78,0.06);">'
            f'<div style="display:flex;align-items:center;gap:0.6rem;">'
            f'<span style="color:{clr};font-size:1rem;">{icon}</span>'
            f'<span style="font-size:0.82rem;color:#6B4A3E;font-weight:500;">{label}</span>'
            f'</div>'
            f'<span style="font-size:1.4rem;font-weight:700;color:{clr};letter-spacing:-0.5px;">{count}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="pv-section-hdr">Projects</div>', unsafe_allow_html=True)
    STATUS_CLR = {"active": "#E07060", "paused": "#C4A882", "completed": "#8E5E4E", "archived": "#A88F87"}
    for project in all_projects:
        ptitle  = _html.escape(_clean(project.get("title") or "Untitled"))
        pstatus = project.get("status", "active")
        health  = project.get("health_score") or 0
        sc = STATUS_CLR.get(pstatus, "#A88F87")
        proj_updates = sum(1 for u in all_updates if u.get("project_id") == project["id"])
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:0.6rem 0;border-bottom:1px solid rgba(142,94,78,0.08);">'
            f'<div>'
            f'<div style="font-size:0.82rem;font-weight:600;color:#2C1810;">{ptitle}</div>'
            f'<div style="font-size:0.68rem;color:{sc};">{pstatus.capitalize()} · {proj_updates} events</div>'
            f'</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:#A88F87;">{health}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
