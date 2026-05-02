import os
import re
import html as _html
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Project",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth
from utils.sidebar import render_sidebar
from services import db_service as db, ai_service as ai
from services import snapshot_service, retrospective_service, search_service
from services import report_service, links_service
from components.snapshot_compare import render_snapshot_compare
from components.ai_chat import render_ai_chat
from components.share_modal import render_share_section
from components.collaborators import render_collaborators
from utils.formatting import health_icon, health_color_class, relative_time

_clean = lambda t: re.sub(r'<[^>]+>', '', _html.unescape(str(t or ''))).strip()
_md    = lambda html: st.markdown(re.sub(r'\n[ \t]*\n', '\n', html), unsafe_allow_html=True)

# Global CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Page-specific CSS
st.markdown("""<style>
/* ── Tab bar redesign ─────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap:           0 !important;
    background:    transparent !important;
    border-radius: 0 !important;
    padding:       0 !important;
    border:        none !important;
    border-bottom: 1px solid rgba(142,94,78,0.12) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius:  0 !important;
    padding:        0.65rem 1.1rem !important;
    font-size:      0.875rem !important;
    font-weight:    500 !important;
    color:          #A88F87 !important;
    background:     transparent !important;
    border:         none !important;
    border-bottom:  2px solid transparent !important;
    margin-bottom:  -1px !important;
    transition:     color 150ms ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color:      #2C1810 !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color:         #2C1810 !important;
    background:    transparent !important;
    border-bottom: 2px solid #2C1810 !important;
}
/* ── Header ───────────────────────────────────── */
.pv-proj-name {
    font-size:   2rem;
    font-weight: 700;
    color:       #2C1810;
    margin:      0 0 0.5rem;
    line-height: 1.2;
}
.pv-category-tag {
    display:        inline-block;
    font-size:      0.68rem;
    font-weight:    600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color:          #6B4A3E;
    border:         1px solid rgba(142,94,78,0.12);
    border-radius:  999px;
    padding:        3px 10px;
    margin-right:   4px;
    margin-bottom:  4px;
}
.pv-health-block  { padding-top: 0.5rem; }
.pv-health-label  { font-size: 0.62rem; color: #A88F87; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 0.3rem; }
.pv-health-display { display: flex; align-items: baseline; gap: 0.35rem; }
.pv-health-num    { font-size: 2.5rem; font-weight: 700; line-height: 1; }
.pv-health-denom  { font-size: 1rem; color: #A88F87; }
.pv-health-insight { font-size: 0.82rem; color: #6B4A3E; font-style: italic; line-height: 1.5; margin: 0.75rem 0 0; }
/* ── Activity rows ────────────────────────────── */
.pv-activity-row {
    display:       flex;
    align-items:   flex-start;
    gap:           0.75rem;
    padding:       0.85rem 0;
    border-bottom: 1px solid rgba(142,94,78,0.12);
}
.pv-activity-row:last-child { border-bottom: none; }
.pv-type-chip {
    font-size:      0.6rem;
    font-weight:    700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding:        3px 7px;
    border-radius:  4px;
    flex-shrink:    0;
    margin-top:     0.2rem;
    white-space:    nowrap;
}
.pv-activity-body { flex: 1; min-width: 0; }
.pv-activity-text { font-size: 0.875rem; color: #2C1810; line-height: 1.5; }
.pv-activity-time { font-size: 0.75rem; color: #A88F87; white-space: nowrap; flex-shrink: 0; padding-top: 0.2rem; }
/* ── Project info panel ───────────────────────── */
.pv-info-panel {
    background:    #FFF8F5;
    border:        1px solid rgba(142,94,78,0.12);
    border-radius: 6px;
    padding:       0.85rem 1rem;
}
.pv-info-row {
    display:         flex;
    justify-content: space-between;
    align-items:     center;
    padding:         0.55rem 0;
    border-bottom:   1px solid rgba(142,94,78,0.12);
}
.pv-info-row:last-child { border-bottom: none; }
.pv-info-label { font-size: 0.68rem; color: #A88F87; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }
.pv-info-value { font-size: 0.82rem; color: #2C1810; font-weight: 500; }
/* ── Timeline ─────────────────────────────────── */
.pv-timeline { position: relative; padding-left: 1.5rem; margin-top: 1rem; }
.pv-timeline::before {
    content:    '';
    position:   absolute;
    left:       3px;
    top:        8px;
    bottom:     8px;
    width:      1px;
    background: rgba(142,94,78,0.12);
}
.pv-tl-item { position: relative; padding-bottom: 1.75rem; padding-left: 0.75rem; }
.pv-tl-item:last-child { padding-bottom: 0; }
.pv-tl-dot {
    position:      absolute;
    left:          -1.25rem;
    top:           0.35rem;
    width:         7px;
    height:        7px;
    border-radius: 50%;
    background:    #2C1810;
}
.pv-tl-title { font-size: 0.875rem; font-weight: 600; color: #2C1810; margin-bottom: 0.2rem; }
.pv-tl-date  { font-size: 0.75rem; color: #A88F87; margin-bottom: 0.35rem; }
.pv-tl-desc  { font-size: 0.8rem; color: #6B4A3E; line-height: 1.5; }
/* ── Radio as minimal text toggle ────────────── */
div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] > div {
    flex-direction: row !important;
    gap:            1.25rem !important;
    flex-wrap:      wrap !important;
    padding:        0.1rem 0 !important;
}
div[data-testid="stRadio"] label {
    cursor:      pointer !important;
    color:       #A88F87 !important;
    font-size:   0.82rem !important;
    font-weight: 500 !important;
    gap:         0 !important;
    transition:  color 150ms !important;
}
div[data-testid="stRadio"] label > div:first-child { display: none !important; }
div[data-testid="stRadio"] input[type="radio"] { display: none !important; }
div[data-testid="stRadio"] label p { margin: 0 !important; }
/* ── Retrospective sections ───────────────────── */
.pv-retro-section {
    background:    #FFF8F5;
    border:        1px solid rgba(142,94,78,0.12);
    border-radius: 8px;
    padding:       16px;
    margin-bottom: 12px;
}
.pv-retro-label {
    font-size:      0.625rem;
    font-weight:    700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom:  10px;
}
.pv-retro-text {
    font-size:   0.875rem;
    color:       #6B4A3E;
    line-height: 1.7;
}
.pv-retro-item {
    display:     flex;
    align-items: flex-start;
    gap:         10px;
    padding:     5px 0;
    font-size:   0.875rem;
    color:       #6B4A3E;
    line-height: 1.5;
}
.pv-retro-dot {
    width:         4px;
    height:        4px;
    border-radius: 50%;
    flex-shrink:   0;
    margin-top:    8px;
}
/* ── Report container ─────────────────────────── */
.pv-report-container {
    background:    #FFF8F5;
    border:        1px solid rgba(142,94,78,0.12);
    border-radius: 8px;
    padding:       32px;
    margin-top:    1rem;
}
.pv-report-sh {
    font-size:      0.75rem;
    font-weight:    600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color:          #A88F87;
    padding-bottom: 8px;
    border-bottom:  1px solid rgba(142,94,78,0.12);
    margin-top:     32px;
    margin-bottom:  12px;
}
.pv-report-sh:first-child { margin-top: 0; }
.pv-report-body {
    font-size:   0.875rem;
    color:       #6B4A3E;
    line-height: 1.8;
    margin:      0 0 6px;
}
.pv-report-item {
    display:     flex;
    align-items: flex-start;
    gap:         10px;
    font-size:   0.875rem;
    color:       #6B4A3E;
    line-height: 1.7;
    margin-bottom: 4px;
}
.pv-report-dot {
    width:         4px;
    height:        4px;
    border-radius: 50%;
    background:    #2C1810;
    flex-shrink:   0;
    margin-top:    9px;
}
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user

if "current_project" not in st.session_state:
    st.error("No project selected.")
    if st.button("Back to Dashboard"):
        st.switch_page("pages/2_dashboard.py")
    st.stop()

project_id = st.session_state["current_project"]
project = db.get_project(project_id)

if not project:
    st.error("Project not found.")
    st.switch_page("pages/2_dashboard.py")
    st.stop()

user_role = db.get_user_role(project_id, user["id"]) or "viewer"
can_edit = user_role in ("owner", "editor")

# ── Sidebar ───────────────────────────────────────────────────────────────────
_all_proj = db.get_projects_for_user(user["id"])
render_sidebar(user, active="project", projects=_all_proj)

# Quick AI chat still accessible via project tabs below

# ── Page Header ───────────────────────────────────────────────────────────────
health = project.get("health_score") or 0
status = project.get("status", "active")

if health > 70:
    health_clr = "#8E5E4E"
elif health >= 50:
    health_clr = "#C4A882"
else:
    health_clr = "#CF6F61"

STATUS_COLORS = {
    "active": "#E88D7D", "paused": "#C4A882",
    "completed": "#8E5E4E", "archived": "#A88F87",
}
status_color = STATUS_COLORS.get(status, "#A88F87")

tags = project.get("tags") or []

col_title, col_health_area = st.columns([6, 3])

with col_title:
    title_safe = _html.escape(_clean(project.get("title") or "Untitled"))
    st.markdown(f'<h1 class="pv-proj-name">{title_safe}</h1>', unsafe_allow_html=True)
    if tags:
        pills = " ".join(
            f'<span class="pv-category-tag">{_html.escape(_clean(t))}</span>'
            for t in tags[:5]
        )
        st.markdown(f'<div>{pills}</div>', unsafe_allow_html=True)
    if project.get("health_explanation"):
        insight = _html.escape(_clean(project["health_explanation"]))
        st.markdown(f'<p class="pv-health-insight">{insight}</p>', unsafe_allow_html=True)

with col_health_area:
    col_hnum, col_hbtn = st.columns([2, 1.5])
    with col_hnum:
        st.markdown(f"""
        <div class="pv-health-block">
            <div class="pv-health-label">Health Score</div>
            <div class="pv-health-display">
                <span class="pv-health-num" style="color:{health_clr};">{health}</span>
                <span class="pv-health-denom">/ 100</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_hbtn:
        st.write("")
        st.write("")
        if can_edit and st.button("Recalculate", key="recalc_health"):
            with st.spinner("Calculating..."):
                state = db.get_project_full_state(project_id)
                score, explanation = ai.calculate_health_score(state)
                db.update_project(project_id, {"health_score": score, "health_explanation": explanation})
            st.rerun()

st.markdown('<div style="height:1px;background:rgba(142,94,78,0.12);margin:1.5rem 0 0;"></div>', unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_overview, tab_updates, tab_timeline, tab_integrations, tab_retro, tab_report, tab_settings = st.tabs([
    "Overview", "Updates", "Timeline", "Integrations", "Retrospective", "Report", "Settings",
])

# ── Type chip helper ──────────────────────────────────────────────────────────
_CHIP = {
    "note":      ("#8E5E4E", "rgba(142,94,78,0.08)",    "NOTE"),
    "decision":  ("#8E5E4E", "#FFF0EB",                 "DECISION"),
    "milestone": ("#7A5C30", "rgba(196,168,130,0.12)",  "MILESTONE"),
    "blocker":   ("#8B3A2A", "rgba(207,111,97,0.1)",    "BLOCKER"),
    "pivot":     ("#8E5E4E", "rgba(232,141,125,0.1)",   "PIVOT"),
}

def _activity_row(u: dict) -> str:
    utype  = u.get("update_type", "note")
    color, bg, label = _CHIP.get(utype, ("#A88F87", "rgba(142,94,78,0.06)", "NOTE"))
    time_s = relative_time(u.get("created_at", ""))
    _raw_text = _clean(u.get("content", ""))
    if len(_raw_text) > 150:
        _raw_text = _raw_text[:150] + "…"
    text   = _html.escape(_raw_text)
    _raw_summ = _clean(u.get("ai_summary") or "")
    if len(_raw_summ) > 150:
        _raw_summ = _raw_summ[:150] + "…"
    summ   = _raw_summ
    summ_h = (
        f'<div style="color:#A88F87;font-size:0.78rem;font-style:italic;margin-top:0.3rem;line-height:1.4;">'
        f'{_html.escape(summ)}</div>'
    ) if summ else ""
    return f"""<div class="pv-activity-row">
        <span class="pv-type-chip" style="color:{color};background:{bg};">{label}</span>
        <div class="pv-activity-body">
            <div class="pv-activity-text">{text}</div>
            {summ_h}
        </div>
        <span class="pv-activity-time">{time_s}</span>
    </div>"""

# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    col_left, col_right = st.columns([13, 7])

    with col_left:
        st.markdown(
            '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
            'letter-spacing:0.1em;font-weight:600;margin-bottom:0.75rem;">Recent Activity</div>',
            unsafe_allow_html=True,
        )
        recent = db.get_updates(project_id, limit=5)
        if not recent:
            st.markdown(
                '<div class="empty-state" style="padding:2rem 0;">'
                '<h3>No updates yet</h3>'
                '<p>Add your first update in the Updates tab.</p></div>',
                unsafe_allow_html=True,
            )
        else:
            rows_html = "".join(_activity_row(u) for u in recent)
            _md(rows_html)

    with col_right:
        # Project info
        github_row = ""
        if project.get("github_repo_url"):
            repo = _html.escape(project["github_repo_url"].split("github.com/")[-1])
            github_row = f"""<div class="pv-info-row">
                <span class="pv-info-label">GitHub</span>
                <span class="pv-info-value" style="color:#2C1810;font-size:0.78rem;">{repo}</span>
            </div>"""

        _md(f"""
        <div class="pv-info-panel">
            <div class="pv-info-row">
                <span class="pv-info-label">Status</span>
                <span class="pv-info-value" style="color:{status_color};">{status.capitalize()}</span>
            </div>
            <div class="pv-info-row">
                <span class="pv-info-label">Role</span>
                <span class="pv-info-value">{user_role.capitalize()}</span>
            </div>
            <div class="pv-info-row">
                <span class="pv-info-label">Created</span>
                <span class="pv-info-value">{project.get('created_at', '')[:10]}</span>
            </div>
            <div class="pv-info-row">
                <span class="pv-info-label">Updated</span>
                <span class="pv-info-value">{relative_time(project.get('updated_at', ''))}</span>
            </div>
            {github_row}
        </div>
        """)

        # Team
        st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
        try:
            collaborators = db.get_collaborators(project_id)
        except Exception:
            collaborators = []

        collab_rows = ""
        for c in collaborators:
            u_info = c.get("users") or {}
            cname = _html.escape(u_info.get("name") or u_info.get("email") or "Unknown")
            crole = _html.escape(c.get("role", "viewer"))
            collab_rows += f"""<div class="pv-info-row">
                <span style="color:#6B4A3E;font-size:0.82rem;">{cname}</span>
                <span style="color:#A88F87;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">{crole}</span>
            </div>"""

        _md(f"""
        <div class="pv-info-panel">
            <div style="font-size:0.68rem;color:#A88F87;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;margin-bottom:0.35rem;">Team</div>
            {collab_rows or '<span style="color:#A88F87;font-size:0.82rem;">Solo project</span>'}
        </div>
        """)

        if can_edit:
            st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
            if st.button("Create Snapshot", use_container_width=True, key="snap_overview"):
                with st.spinner("Creating snapshot with AI narrative..."):
                    snap = snapshot_service.create_snapshot(project_id, user["id"])
                st.success(f"Snapshot created: {snap['title']}")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# UPDATES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_updates:
    if can_edit:
        st.markdown(
            '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
            'letter-spacing:0.1em;font-weight:600;margin-bottom:0.75rem;">Add Update</div>',
            unsafe_allow_html=True,
        )
        with st.form("add_update_form", clear_on_submit=True):
            upd_content = st.text_area(
                "What happened?",
                placeholder="Describe this update — a decision made, progress, a blocker, or a milestone...",
                height=100,
                label_visibility="collapsed",
            )
            col_type_sel, col_add_btn = st.columns([4, 1])
            with col_type_sel:
                utype = st.radio(
                    "Type",
                    ["note", "decision", "milestone", "blocker", "pivot"],
                    format_func=lambda x: x.upper(),
                    horizontal=True,
                    key="upd_type_radio",
                )
            with col_add_btn:
                st.write("")
                submitted = st.form_submit_button("Add Update", type="primary", use_container_width=True)

        if submitted:
            if not upd_content.strip():
                st.error("Content cannot be empty.")
            else:
                with st.spinner("Saving and generating AI summary..."):
                    ai_summary = ai.summarize_update(upd_content.strip(), utype, project["title"])
                    update = db.add_update(project_id, user["id"], upd_content.strip(), utype, ai_summary=ai_summary)
                    search_service.embed_update(update, project_id)
                st.success("Update added!")
                st.rerun()

        st.markdown('<div style="height:1px;background:rgba(142,94,78,0.12);margin:1.25rem 0;"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
        'letter-spacing:0.1em;font-weight:600;margin-bottom:0.5rem;">Activity Log</div>',
        unsafe_allow_html=True,
    )
    all_updates = db.get_updates(project_id, limit=200)

    if not all_updates:
        st.markdown(
            '<div class="empty-state" style="padding:2.5rem 0;"><h3>No updates yet</h3>'
            '<p>Start tracking this project by adding your first update above.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        _filter_map = {
            "all": "All", "note": "Notes", "decision": "Decisions",
            "milestone": "Milestones", "blocker": "Blockers", "pivot": "Pivots",
        }
        _active_filter = st.radio(
            "Filter updates",
            list(_filter_map.keys()),
            format_func=lambda x: _filter_map[x],
            horizontal=True,
            key=f"upd_filter_{project_id}",
            label_visibility="collapsed",
        )

        filtered = (
            all_updates if _active_filter == "all"
            else [u for u in all_updates if u.get("update_type") == _active_filter]
        )

        st.markdown(
            f'<div style="color:#A88F87;font-size:0.75rem;margin:0.5rem 0 0.25rem;">'
            f'{len(filtered)} update{"s" if len(filtered) != 1 else ""}</div>',
            unsafe_allow_html=True,
        )

        for u in filtered:
            col_row, col_del = st.columns([11, 1])
            with col_row:
                _md(_activity_row(u))
            with col_del:
                if can_edit and st.button("×", key=f"del_{u['id']}", help="Delete update"):
                    db.delete_update(u["id"])
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_timeline:
    col_tl_hdr, col_tl_btn = st.columns([5, 1.2])
    with col_tl_hdr:
        st.markdown(
            '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
            'letter-spacing:0.1em;font-weight:600;margin-bottom:0.75rem;">Project Timeline</div>',
            unsafe_allow_html=True,
        )
    with col_tl_btn:
        if can_edit and st.button("New Snapshot", use_container_width=True, key="new_snap_tl"):
            with st.spinner("Creating snapshot..."):
                snap = snapshot_service.create_snapshot(project_id, user["id"])
            st.success("Snapshot created!")
            st.rerun()

    snapshots = db.get_snapshots(project_id)

    if not snapshots:
        st.markdown(
            '<div class="empty-state" style="padding:3rem 0;">'
            '<h3>No snapshots yet</h3>'
            '<p>Snapshots capture the state of your project with an AI-generated narrative.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="pv-timeline">', unsafe_allow_html=True)
        for snap in snapshots:
            snap_title = _html.escape(_clean(snap.get("title") or "Snapshot"))
            snap_date  = (snap.get("created_at") or "")[:10]
            snap_desc  = _clean(snap.get("narrative_summary") or snap.get("description") or "")
            snap_desc_safe = _html.escape(snap_desc[:200]) if snap_desc else ""
            _md(f"""
            <div class="pv-tl-item">
                <div class="pv-tl-dot"></div>
                <div class="pv-tl-title">{snap_title}</div>
                <div class="pv-tl-date">{snap_date}</div>
                {f'<div class="pv-tl-desc">{snap_desc_safe}</div>' if snap_desc_safe else ''}
            </div>
            """)
        st.markdown('</div>', unsafe_allow_html=True)

        if can_edit:
            st.markdown('<div style="height:1px;background:rgba(142,94,78,0.12);margin:1.5rem 0;"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
                'letter-spacing:0.1em;font-weight:600;margin-bottom:0.5rem;">Rollback</div>',
                unsafe_allow_html=True,
            )
            snap_opts = {
                s["id"]: f"{s.get('title', 'Snapshot')} — {(s.get('created_at') or '')[:10]}"
                for s in snapshots
            }
            selected_sid = st.selectbox(
                "Choose snapshot",
                list(snap_opts.keys()),
                format_func=lambda x: snap_opts[x],
            )
            if st.button("Rollback to selected snapshot", type="primary", key="do_rollback"):
                with st.spinner("Rolling back..."):
                    ok = snapshot_service.rollback_to_snapshot(selected_sid, user["id"], project_id)
                if ok:
                    st.success("Rolled back. A post-rollback snapshot was created.")
                    st.rerun()
                else:
                    st.error("Rollback failed.")

        if len(snapshots) >= 2:
            st.markdown('<div style="height:1px;background:rgba(142,94,78,0.12);margin:1.5rem 0;"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
                'letter-spacing:0.1em;font-weight:600;margin-bottom:0.75rem;">Compare Snapshots</div>',
                unsafe_allow_html=True,
            )
            render_snapshot_compare(snapshots, project_id, user["id"])

# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATIONS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_integrations:
    int_tab_github, int_tab_ai = st.tabs(["GitHub", "AI Providers"])

    with int_tab_github:
        st.markdown(
            '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
            'letter-spacing:0.1em;font-weight:600;margin-bottom:0.75rem;">Connect GitHub Repository</div>',
            unsafe_allow_html=True,
        )
        github_url = project.get("github_repo_url") or ""
        new_github = st.text_input(
            "Repository URL",
            value=github_url,
            placeholder="https://github.com/owner/repo",
            key="github_url_input",
        )

        col_save, col_sync = st.columns(2)
        with col_save:
            if st.button("Save URL", use_container_width=True):
                if can_edit:
                    db.update_project(project_id, {"github_repo_url": new_github.strip() or None})
                    st.success("Saved!")
                    st.rerun()
                else:
                    st.error("Edit permission required.")
        with col_sync:
            if new_github and st.button("Sync Now", use_container_width=True, type="primary"):
                token = st.session_state.get("github_token") or os.getenv("GITHUB_TOKEN", "")
                if not token:
                    st.warning("Add your GitHub token in Settings first.")
                else:
                    with st.spinner("Syncing GitHub data..."):
                        from services import github_service
                        result = github_service.sync_repo(new_github.strip(), project_id)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success(f"Synced: {result['commits']} commits, {result['pull_requests']} PRs, {result['issues']} issues")
                        if result.get("errors"):
                            st.warning("Partial errors: " + "; ".join(result["errors"]))

        if new_github:
            st.markdown('<div style="height:1px;background:rgba(142,94,78,0.12);margin:1.25rem 0;"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
                'letter-spacing:0.1em;font-weight:600;margin-bottom:0.75rem;">Recent Commits</div>',
                unsafe_allow_html=True,
            )
            token = st.session_state.get("github_token") or os.getenv("GITHUB_TOKEN", "")
            if token:
                with st.spinner("Loading commits..."):
                    from services import github_service
                    commits = github_service.get_recent_commits(new_github, limit=10)
                for c in commits:
                    sha_safe = _html.escape(str(c.get("sha", "")))
                    msg_safe = _html.escape(_clean(str(c.get("message", ""))))
                    author_safe = _html.escape(str(c.get("author", "")))
                    date_safe = _html.escape(str(c.get("date", "")))
                    st.markdown(f"""
                    <div class="pv-card" style="padding:0.75rem 1rem;margin-bottom:0.4rem;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-family:monospace;color:#2C1810;font-size:0.82rem;">{sha_safe[:8]}</span>
                            <span style="color:#A88F87;font-size:0.78rem;">{date_safe}</span>
                        </div>
                        <div style="margin-top:0.25rem;font-size:0.875rem;color:#2C1810;">{msg_safe}</div>
                        <div style="color:#A88F87;font-size:0.78rem;margin-top:0.2rem;">{author_safe}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Add your GitHub token in Settings to view commits.")

    with int_tab_ai:
        st.markdown(
            '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
            'letter-spacing:0.1em;font-weight:600;margin-bottom:0.75rem;">AI Provider Status</div>',
            unsafe_allow_html=True,
        )
        openai_key    = st.session_state.get("openai_key") or os.getenv("OPENAI_API_KEY", "")
        groq_key      = st.session_state.get("groq_key") or os.getenv("GROQ_API_KEY", "")
        active_provider = ai._provider()

        col1, col2 = st.columns(2)
        col1.metric(
            "Groq (Llama 3.3 70B)",
            "Active" if active_provider == "groq" else ("Configured" if groq_key else "Not set"),
        )
        col2.metric("OpenAI (Embeddings)", "Configured" if openai_key else "Not set")
        st.caption(f"Active AI: **{active_provider.capitalize() if active_provider != 'none' else 'None — add GROQ_API_KEY in Settings'}**")

        st.markdown('<div style="height:1px;background:rgba(142,94,78,0.12);margin:1.25rem 0;"></div>', unsafe_allow_html=True)

        if can_edit and st.button("Re-index project (rebuild embeddings)", use_container_width=True):
            if not openai_key:
                st.error("OpenAI API key required for embeddings. Add it in Settings.")
            else:
                with st.spinner("Re-indexing all updates and snapshots..."):
                    result = search_service.reindex_project(project_id)
                st.success(f"Indexed {result['total']} items ({result['updates_indexed']} updates, {result['snapshots_indexed']} snapshots)")

        st.markdown('<div style="height:1px;background:rgba(142,94,78,0.12);margin:1.25rem 0;"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
            'letter-spacing:0.1em;font-weight:600;margin-bottom:0.5rem;">Upload ChatGPT Export</div>',
            unsafe_allow_html=True,
        )
        st.caption("Export your ChatGPT conversations (Settings → Export data) and upload here to index them.")
        uploaded = st.file_uploader("conversations.json", type=["json"])
        if uploaded and can_edit:
            import json as _json
            try:
                data = _json.load(uploaded)
                convos = data if isinstance(data, list) else data.get("conversations", [])
                count = 0
                with st.spinner(f"Indexing {len(convos)} conversations..."):
                    for convo in convos[:50]:
                        title = convo.get("title", "ChatGPT conversation")
                        messages = convo.get("mapping", {})
                        text_parts = []
                        for node in messages.values():
                            msg = node.get("message")
                            if msg and msg.get("author", {}).get("role") == "user":
                                parts = msg.get("content", {}).get("parts", [])
                                text_parts.extend([p for p in parts if isinstance(p, str)])
                        content_text = f"ChatGPT: {title}\n" + " ".join(text_parts)[:2000]
                        embedding = ai.generate_embedding(content_text)
                        if embedding:
                            from services.auth_service import get_supabase_admin
                            import uuid
                            get_supabase_admin().table("embeddings").upsert({
                                "project_id": project_id,
                                "source_type": "ai_conversation",
                                "source_id": str(uuid.uuid4()),
                                "content": content_text,
                                "embedding": embedding,
                                "metadata": {"title": title, "source": "chatgpt"},
                            }, on_conflict="source_id,project_id").execute()
                            count += 1
                st.success(f"Indexed {count} ChatGPT conversations.")
            except Exception as e:
                st.error(f"Failed to parse file: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# RETROSPECTIVE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_retro:
    past_retros = db.get_retrospectives(project_id)

    col_gen, col_spacer = st.columns([2, 3])
    with col_gen:
        if can_edit and st.button("Generate Retrospective", type="primary", use_container_width=True):
            with st.spinner("Analyzing project data and generating retrospective..."):
                try:
                    retro = retrospective_service.generate_and_store(project_id, user["id"])
                    st.success("Retrospective generated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not generate retrospective: {e}")

    if not past_retros:
        st.markdown(
            '<div class="empty-state" style="padding:2.5rem 0;">'
            '<h3>No retrospectives yet</h3>'
            '<p>Generate your first AI retrospective above.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        retro_options = {r["id"]: r["created_at"][:16].replace("T", " ") for r in past_retros}
        selected_retro_id = st.selectbox(
            "View retrospective",
            list(retro_options.keys()),
            format_func=lambda x: retro_options[x],
            label_visibility="collapsed",
        )
        retro   = next(r for r in past_retros if r["id"] == selected_retro_id)
        content = retro.get("content") or {}

        if isinstance(content, str):
            import json as _json
            try:
                content = _json.loads(content)
            except Exception:
                st.markdown(content)
                content = {}

        summary = content.get("executive_summary", "")
        if summary and any(k in summary.lower() for k in ("generation failed", "error code", "credit balance")):
            st.error(f"This retrospective failed to generate. Try generating a new one. Reason: {summary[:200]}")
            content = {}
        elif summary:
            st.markdown(f"""
            <div class="pv-retro-section" style="border-left:3px solid #2C1810;">
                <div class="pv-retro-label" style="color:#2C1810;">Executive Summary</div>
                <div class="pv-retro-text">{_html.escape(_clean(summary))}</div>
            </div>
            """, unsafe_allow_html=True)

        def _retro_items(items, dot_color):
            if not items:
                return '<div class="pv-retro-text" style="color:#A88F87;">No items recorded.</div>'
            out = ""
            for item in items:
                if isinstance(item, dict):
                    text = f"{item.get('decision', '')} ({item.get('date', '')}) — {item.get('impact', '')}"
                else:
                    text = str(item)
                out += (
                    f'<div class="pv-retro-item">'
                    f'<span class="pv-retro-dot" style="background:{dot_color};"></span>'
                    f'<span>{_html.escape(_clean(text))}</span>'
                    f'</div>'
                )
            return out

        has_content = any(content.get(k) for k in ("went_well", "key_decisions", "didnt_work", "patterns_risks"))
        if has_content:
            col_a, col_b = st.columns(2)
            with col_a:
                if content.get("went_well"):
                    st.markdown(f"""
                    <div class="pv-retro-section" style="border-left:3px solid #E88D7D;">
                        <div class="pv-retro-label" style="color:#E88D7D;">Went Well</div>
                        {_retro_items(content["went_well"], "#E88D7D")}
                    </div>
                    """, unsafe_allow_html=True)
                if content.get("key_decisions"):
                    st.markdown(f"""
                    <div class="pv-retro-section" style="border-left:3px solid #2C1810;">
                        <div class="pv-retro-label" style="color:#2C1810;">Key Decisions</div>
                        {_retro_items(content["key_decisions"], "#2C1810")}
                    </div>
                    """, unsafe_allow_html=True)
            with col_b:
                if content.get("didnt_work"):
                    st.markdown(f"""
                    <div class="pv-retro-section" style="border-left:3px solid #CF6F61;">
                        <div class="pv-retro-label" style="color:#CF6F61;">Didn't Work</div>
                        {_retro_items(content["didnt_work"], "#CF6F61")}
                    </div>
                    """, unsafe_allow_html=True)
                if content.get("patterns_risks"):
                    st.markdown(f"""
                    <div class="pv-retro-section" style="border-left:3px solid #C4A882;">
                        <div class="pv-retro-label" style="color:#C4A882;">Patterns & Risks</div>
                        {_retro_items(content["patterns_risks"], "#C4A882")}
                    </div>
                    """, unsafe_allow_html=True)

        if content.get("recommendations"):
            st.markdown(f"""
            <div class="pv-retro-section" style="border-left:3px solid #E88D7D;">
                <div class="pv-retro-label" style="color:#E88D7D;">Recommendations</div>
                {_retro_items(content["recommendations"], "#E88D7D")}
            </div>
            """, unsafe_allow_html=True)

        col_meta, col_export = st.columns([4, 1])
        with col_meta:
            st.markdown(
                f'<p style="color:#A88F87;font-size:0.75rem;margin-top:0.5rem;">Generated {retro["created_at"][:10]}</p>',
                unsafe_allow_html=True,
            )
        with col_export:
            if st.button("Export as Markdown", key="export_retro_md", use_container_width=True):
                md = f"# Retrospective — {project['title']}\n\n*Generated: {retro['created_at'][:10]}*\n\n"
                if content.get("executive_summary"):
                    md += f"## Executive Summary\n{content['executive_summary']}\n\n"
                for section, heading in [
                    ("went_well", "What Went Well"), ("didnt_work", "What Didn't Work"),
                    ("patterns_risks", "Patterns & Risks"), ("recommendations", "Recommendations"),
                ]:
                    if content.get(section):
                        md += f"## {heading}\n" + "\n".join(f"- {i}" for i in content[section]) + "\n\n"
                st.download_button(
                    "Download .md", data=md,
                    file_name=f"retro_{project['title'].replace(' ', '_')}.md",
                    mime="text/markdown",
                )

# ═══════════════════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_report:
    def _inline_md(text):
        text = _html.escape(_clean(text))
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#2C1810;font-weight:600;">\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        return text

    def _md_to_report_html(md_text):
        lines = md_text.split('\n')
        parts = ['<div class="pv-report-container">']
        for line in lines:
            line = line.rstrip()
            if not line.strip():
                continue
            if line.startswith('### '):
                parts.append(f'<div class="pv-report-sh" style="font-size:0.65rem;">{_html.escape(_clean(line[4:]))}</div>')
            elif line.startswith('## '):
                parts.append(f'<div class="pv-report-sh">{_html.escape(_clean(line[3:]))}</div>')
            elif line.startswith('# '):
                parts.append(f'<div class="pv-report-sh">{_html.escape(_clean(line[2:]))}</div>')
            elif re.match(r'^[-*]\s+', line):
                text = _inline_md(re.sub(r'^[-*]\s+', '', line))
                parts.append(f'<div class="pv-report-item"><span class="pv-report-dot"></span><span>{text}</span></div>')
            elif re.match(r'^\d+\.\s+', line):
                text = _inline_md(re.sub(r'^\d+\.\s+', '', line))
                parts.append(f'<div class="pv-report-item"><span class="pv-report-dot"></span><span>{text}</span></div>')
            else:
                parts.append(f'<p class="pv-report-body">{_inline_md(line)}</p>')
        parts.append('</div>')
        return '\n'.join(parts)

    col_gen, col_spacer = st.columns([2, 4])
    with col_gen:
        if st.button("Generate Report", type="primary", use_container_width=True, key="gen_report"):
            with st.spinner("Analysing project data..."):
                try:
                    report_md = report_service.generate_report(project_id)
                    st.session_state[f"report_{project_id}"] = report_md
                except Exception as e:
                    st.error(f"Could not generate report: {e}")

    if f"report_{project_id}" in st.session_state:
        report_md = st.session_state[f"report_{project_id}"]
        st.markdown(_md_to_report_html(report_md), unsafe_allow_html=True)

        col_spacer2, col_dl_md, col_dl_pdf = st.columns([3, 1.2, 1.2])
        with col_dl_md:
            st.download_button(
                "Export as Markdown",
                data=report_md,
                file_name=f"report_{project['title'].replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_dl_pdf:
            if st.button("Download as PDF", use_container_width=True, key="dl_pdf"):
                with st.spinner("Generating PDF..."):
                    try:
                        pdf_bytes = report_service.generate_pdf(report_md, project["title"])
                        st.download_button(
                            "Click to download",
                            data=pdf_bytes,
                            file_name=f"report_{project['title'].replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="dl_pdf_actual",
                        )
                    except Exception as e:
                        st.error(f"PDF generation failed: {e}")

    st.markdown('<div style="height:1px;background:rgba(142,94,78,0.12);margin:1.5rem 0;"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.7rem;color:#A88F87;text-transform:uppercase;'
        'letter-spacing:0.1em;font-weight:600;margin-bottom:0.25rem;">Deep Analysis</div>',
        unsafe_allow_html=True,
    )
    st.caption("Four AI insight cards: velocity, scope, collaboration, and completion forecast.")

    _STATUS_COLOR = {"green": "#8E5E4E", "yellow": "#C4A882", "red": "#CF6F61", "blue": "#E88D7D"}

    col_run, _ = st.columns([2, 4])
    with col_run:
        if st.button("Run Deep Analysis", use_container_width=True, key="run_analysis"):
            with st.spinner("Analyzing project patterns..."):
                try:
                    analysis = report_service.generate_deep_analysis(project_id)
                    st.session_state[f"analysis_{project_id}"] = analysis
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

    if f"analysis_{project_id}" in st.session_state:
        analysis = st.session_state[f"analysis_{project_id}"]
        _INSIGHT_META = [
            ("velocity_trend",        "Velocity Trend",       ),
            ("scope_analysis",        "Scope Analysis",       ),
            ("collaboration_pattern", "Collaboration Pattern",),
            ("predictive_completion", "Predictive Completion",),
        ]
        col_a, col_b = st.columns(2)
        for i, (key, title) in enumerate(_INSIGHT_META):
            data  = analysis.get(key, {})
            color = _STATUS_COLOR.get(data.get("status", "yellow"), "#C4A882")
            card_col = col_a if i % 2 == 0 else col_b
            with card_col:
                st.markdown(f"""
                <div class="pv-card" style="border-left:3px solid {color};padding:1rem;">
                    <div style="font-size:0.68rem;color:#A88F87;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">{title}</div>
                    <div style="margin-top:0.4rem;font-weight:600;color:#2C1810;">{_html.escape(_clean(data.get('insight', '')))}</div>
                    <div style="margin-top:0.25rem;color:#6B4A3E;font-size:0.82rem;">{_html.escape(_clean(data.get('detail', '')))}</div>
                    <div style="margin-top:0.5rem;">
                        <span style="background:{color}22;color:{color};padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:600;text-transform:uppercase;">{data.get('status','').upper()}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_settings:
    if not can_edit:
        st.warning("You have viewer access and cannot edit settings.")

    settings_tabs = st.tabs(["Project", "Sharing", "Collaborators", "Danger Zone"])

    with settings_tabs[0]:
        st.markdown("### Edit Project")
        if can_edit:
            with st.form("edit_project_form"):
                new_title = st.text_input("Name", value=project.get("title", ""))
                new_desc  = st.text_area("Description", value=project.get("description") or "", height=80)
                new_status = st.selectbox(
                    "Status",
                    ["active", "paused", "completed", "archived"],
                    index=["active", "paused", "completed", "archived"].index(project.get("status", "active")),
                )
                tags_str     = ", ".join(project.get("tags") or [])
                new_tags_raw = st.text_input("Tags (comma-separated)", value=tags_str)
                if st.form_submit_button("Save Changes", type="primary"):
                    if not new_title.strip():
                        st.error("Name cannot be empty.")
                    else:
                        db.update_project(project_id, {
                            "title":       new_title.strip(),
                            "description": new_desc.strip(),
                            "status":      new_status,
                            "tags":        [t.strip() for t in new_tags_raw.split(",") if t.strip()],
                        })
                        st.success("Saved!")
                        st.rerun()

    with settings_tabs[1]:
        render_share_section(project, can_edit)

    with settings_tabs[2]:
        try:
            render_collaborators(project_id, user["id"], can_edit)
        except Exception as e:
            st.error(f"Could not load collaborators: {e}")

    with settings_tabs[3]:
        if can_edit:
            st.markdown("### Delete Project")
            st.warning("This permanently deletes the project, all updates, snapshots, and integrations.")
            confirm = st.text_input("Type project name to confirm", placeholder=project["title"])
            if st.button("Delete Project", type="primary"):
                if confirm.strip() == project["title"]:
                    db.delete_project(project_id)
                    del st.session_state["current_project"]
                    st.switch_page("pages/2_dashboard.py")
                else:
                    st.error("Name doesn't match.")
