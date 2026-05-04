import os
import re
import html as _html
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth
from utils.formatting import relative_time, clean_description
from utils.sidebar import render_sidebar
from services.db_service import (
    get_projects_for_user, create_project,
    get_recent_updates_for_user, get_milestones_for_user,
)
from components.import_modal import render_import_modal

_clean = lambda t: re.sub(r'<[^>]+>', '', _html.unescape(str(t or ''))).strip()
_md    = lambda html: st.markdown(re.sub(r'\n[ \t]*\n', '\n', html), unsafe_allow_html=True)

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""<style>
/* ── Dashboard ────────────────────────────────────────────────────── */
.dash-greeting {
    font-size: 2.1rem; font-weight: 700; color: #2C1810;
    letter-spacing: -0.8px; line-height: 1.2; margin: 0 0 0.25rem;
}
.dash-micro { font-size: 0.875rem; color: #7A6560; margin: 0; }

/* Pulse compact */
.pulse-pill {
    display: inline-flex; align-items: center; gap: 0.6rem;
    background: #FFE4D8; border: 1px solid rgba(232,141,125,0.4);
    border-radius: 16px; padding: 0.65rem 1.1rem;
    box-shadow: 0 2px 8px rgba(232,141,125,0.12);
}
.pulse-icon { font-size: 1.1rem; }
.pulse-meta { display: flex; flex-direction: column; }
.pulse-lbl { font-size: 0.55rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #E07060; }
.pulse-val { font-size: 1.35rem; font-weight: 700; color: #2C1810; letter-spacing: -0.5px; line-height: 1.1; }

/* Section label */
.sec-lbl {
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #A88F87; margin: 0 0 0.85rem 0;
    height: 1rem; display: flex; align-items: center;
}

/* Featured project card — compact for vertical balance */
.feat-card {
    background: #FFFFFF; border: 1px solid rgba(142,94,78,0.2);
    border-radius: 16px; overflow: hidden;
    box-shadow: 0 3px 14px rgba(142,94,78,0.1);
    margin-bottom: 0;
}
.feat-visual {
    height: 70px; position: relative; overflow: hidden;
    background: linear-gradient(135deg, #E07060 0%, #C4A882 60%, #FFE4D8 100%);
    display: flex; align-items: flex-end; padding: 0.6rem 0.85rem;
}
.feat-badge {
    font-size: 0.58rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; background: #FFFFFF; color: #E07060;
    border-radius: 999px; padding: 3px 10px; display: inline-block;
}
.feat-body { padding: 0.85rem 1rem 1rem; }
.feat-title { font-size: 1rem; font-weight: 700; color: #2C1810; letter-spacing: -0.3px; margin: 0 0 0.2rem; line-height: 1.2; }
.feat-desc { font-size: 0.75rem; color: #7A6560; line-height: 1.5; margin: 0 0 0.6rem;
             display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
             overflow: hidden; }
.feat-prog-lbl { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem; }
.feat-prog-lbl span { font-size: 0.58rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #A88F87; }
.feat-prog-wrap { background: rgba(142,94,78,0.1); border-radius: 999px; height: 7px; overflow: hidden; }
.feat-prog-bar { height: 100%; background: linear-gradient(90deg, #D4543F, #C4A882); border-radius: 999px; }
.feat-link { font-size: 0.78rem; font-weight: 600; color: #E07060; text-decoration: none; }

/* Project row — compact stacked layout */
.proj-row {
    display: flex; align-items: center; gap: 0.5rem;
    background: #FFFFFF; border: 1px solid rgba(142,94,78,0.18);
    border-radius: 14px; padding: 0.85rem 1rem; margin-bottom: 0.5rem;
    box-shadow: 0 2px 7px rgba(142,94,78,0.08);
    transition: border-color 150ms ease, box-shadow 150ms ease;
    min-width: 0;
}
.proj-row:hover { border-color: rgba(224,112,96,0.4); box-shadow: 0 4px 14px rgba(142,94,78,0.12); }
.proj-row-left { flex: 1 1 auto; min-width: 0; overflow: hidden; }
.proj-row-name {
    font-size: 0.88rem; font-weight: 600; color: #2C1810;
    letter-spacing: -0.15px; margin-bottom: 0.2rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 100%;
}
.proj-row-meta {
    display: flex; align-items: center; gap: 0.3rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex-wrap: nowrap;
}
.proj-row-dot { width: 5px; height: 5px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.proj-row-status { font-size: 0.7rem; font-weight: 600; flex-shrink: 0; }
.proj-row-time { font-size: 0.68rem; color: #A88F87; overflow: hidden; text-overflow: ellipsis; }
.proj-row-tags {
    display: flex; gap: 0.25rem; margin-top: 0.3rem;
    flex-wrap: nowrap; overflow: hidden;
}
.proj-row-tag {
    font-size: 0.55rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: #8E5E4E; background: #FFE4D8;
    border: 1px solid rgba(232,141,125,0.35); border-radius: 999px;
    padding: 1px 7px; flex-shrink: 0;
    max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
/* Right side: stack score + bar vertically so they never overlap text */
.proj-row-right {
    display: flex; flex-direction: column; align-items: flex-end;
    gap: 0.3rem; flex-shrink: 0; margin-left: 0.5rem;
}
.proj-row-score {
    font-size: 1.25rem; font-weight: 700; letter-spacing: -0.5px;
    line-height: 1;
}
.proj-prog-wrap {
    width: 56px; height: 5px; background: rgba(142,94,78,0.08);
    border-radius: 999px; overflow: hidden;
}
.proj-prog-fill { height: 100%; border-radius: 999px; }

/* Focus card */
.focus-card {
    background: #FFFFFF; border: 1px solid rgba(142,94,78,0.2);
    border-radius: 20px; padding: 1.1rem 1.25rem;
    box-shadow: 0 2px 10px rgba(142,94,78,0.09);
}
.focus-hdr { font-size: 0.78rem; font-weight: 600; color: #2C1810; margin-bottom: 0.8rem; }
.focus-row { display: flex; align-items: flex-start; gap: 0.6rem; padding: 0.55rem 0; border-bottom: 1px solid rgba(142,94,78,0.06); }
.focus-row:last-child { border-bottom: none; padding-bottom: 0; }
.focus-ring { width: 17px; height: 17px; border-radius: 50%; border: 1.5px solid rgba(142,94,78,0.25); flex-shrink: 0; margin-top: 1px; display: flex; align-items: center; justify-content: center; }
.focus-ring-done { background: #E07060; border-color: #E07060; }
.focus-check { color: #fff; font-size: 8px; font-weight: 800; line-height: 1; }
.focus-body { flex: 1; min-width: 0; }
.focus-text { font-size: 0.8rem; color: #2C1810; line-height: 1.4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.focus-proj { font-size: 0.67rem; color: #A88F87; margin-top: 0.1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.focus-time { font-size: 0.6rem; font-weight: 600; color: #E07060; background: rgba(232,141,125,0.1); border-radius: 999px; padding: 2px 7px; flex-shrink: 0; margin-top: 2px; white-space: nowrap; }

/* Tighten dashboard column spacing — featured cards flow with their buttons */
section.main [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] {
    gap: 0.5rem !important;
}
section.main [data-testid="column"] div.stButton {
    margin-top: 0.4rem !important;
    margin-bottom: 0.6rem !important;
}

/* Timeline bottom */
.tl-section {
    background: #FFFFFF; border: 1px solid rgba(142,94,78,0.2);
    border-radius: 20px; padding: 1.3rem 1.5rem;
    box-shadow: 0 2px 10px rgba(142,94,78,0.09);
}
.tl-hdr { font-size: 1rem; font-weight: 700; color: #2C1810; letter-spacing: -0.3px; margin-bottom: 1.1rem; }
.tl-nodes { display: flex; gap: 2rem; flex-wrap: wrap; }
.tl-node { display: flex; align-items: flex-start; gap: 0.7rem; }
.tl-dot-col { display: flex; flex-direction: column; align-items: center; gap: 0; }
.tl-dot { width: 11px; height: 11px; border-radius: 50%; flex-shrink: 0; }
.tl-dash { width: 1px; flex: 1; min-height: 30px; background: rgba(142,94,78,0.12); margin-top: 3px; }
.tl-when { font-size: 0.58rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 0.2rem; }
.tl-name { font-size: 0.85rem; font-weight: 600; color: #2C1810; }
.tl-detail { font-size: 0.72rem; color: #A88F87; margin-top: 0.1rem; }

/* Stat block */
.stat-block {
    background: #FFFFFF; border: 1px solid rgba(142,94,78,0.2);
    border-radius: 20px; padding: 1.3rem 1.5rem;
    box-shadow: 0 2px 10px rgba(142,94,78,0.09);
    text-align: center; height: 100%;
}
.stat-lbl { font-size: 0.55rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #A88F87; margin-bottom: 0.4rem; }
.stat-num { font-size: 2.2rem; font-weight: 700; color: #2C1810; letter-spacing: -1.5px; line-height: 1; }
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user

# Handle Google Drive OAuth callback
_gdrive_code  = st.query_params.get("code")
_gdrive_state = st.query_params.get("state", "")
if _gdrive_code and _gdrive_state == "gdrive_import" and not st.session_state.get("gdrive_token"):
    try:
        import os as _os
        from google_auth_oauthlib.flow import Flow as _Flow
        _app_url = _os.getenv("APP_URL", "http://localhost:8501")
        _flow = _Flow.from_client_config(
            {"web": {
                "client_id": _os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": _os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "redirect_uris": [f"{_app_url}/2_dashboard"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }},
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
            redirect_uri=f"{_app_url}/2_dashboard",
        )
        _flow.fetch_token(code=_gdrive_code)
        st.session_state["gdrive_token"] = _flow.credentials.token
        st.query_params.clear()
        st.session_state["show_import_modal"] = True
        st.rerun()
    except Exception as _e:
        st.query_params.clear()
        st.error(f"Google Drive connection failed: {_e}")

# ── Load data ──────────────────────────────────────────────────────────────────
projects        = get_projects_for_user(user["id"])
project_ids     = [p["id"] for p in projects] if projects else []
project_map     = {p["id"]: _clean(p.get("title", "")) for p in projects}
recent_updates  = get_recent_updates_for_user(project_ids, limit=12) if project_ids else []
milestones      = get_milestones_for_user(project_ids, limit=6)      if project_ids else []
total_updates   = len(get_recent_updates_for_user(project_ids, limit=200)) if project_ids else 0

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar(user, active="dashboard", projects=projects)

# ── Hero ───────────────────────────────────────────────────────────────────────
# Server-side hour fallback (UTC); browser JS will overwrite the greeting client-side
_hour = datetime.utcnow().hour
_name_safe = _html.escape(user.get("name") or "")
_first     = _html.escape((_name_safe or "there").split()[0])

if 0 <= _hour < 5:
    _greeting = f"Still up, {_first}?"
    _micros = [
        "Night owl spotted. The best ideas come after midnight.",
        "Not kept working late nights, I see.",
        "The world's asleep — this is your edge.",
        "Late nights and big dreams. Respect.",
    ]
    _pulse_icon = "🌙"
elif 5 <= _hour < 12:
    _greeting = f"Good morning, {_first}"
    _micros = [
        "Early start. Your projects are grateful.",
        "Fresh day, fresh momentum. Let's go.",
        "The best builders start before the world wakes up.",
        "Morning clarity is a superpower. Use it.",
    ]
    _pulse_icon = "☀️"
elif 12 <= _hour < 17:
    _greeting = f"Good afternoon, {_first}"
    _micros = [
        "Deep work hours. Make them count.",
        "Every update brings you closer to launch.",
        "Clarity builds momentum. Keep going.",
        "Your work is tracked, your progress is real.",
    ]
    _pulse_icon = "🌤️"
elif 17 <= _hour < 21:
    _greeting = f"Good evening, {_first}"
    _micros = [
        "Wrapping up strong. Log your wins.",
        "End of day check-in. How did it go?",
        "Evening reflection fuels tomorrow.",
        "The best teams review before they rest.",
    ]
    _pulse_icon = "🌆"
else:
    _greeting = f"Burning the midnight oil, {_first}?"
    _micros = [
        "Late night mode. The quiet hours hit different.",
        "Still here? Your projects appreciate the dedication.",
        "Night shifts build empires. Or at least good software.",
        "Almost tomorrow. Make this session count.",
    ]
    _pulse_icon = "🌙"

_micro = _micros[_hour % len(_micros)]

avg_health = int(sum(p.get("health_score", 0) or 0 for p in projects) / max(len(projects), 1))

col_hero, col_pulse = st.columns([6, 3])
with col_hero:
    st.markdown(
        f'<h1 class="dash-greeting" id="pv-greeting">{_greeting}</h1>'
        f'<p class="dash-micro" id="pv-micro">{_micro}</p>',
        unsafe_allow_html=True,
    )
with col_pulse:
    st.markdown('<div style="height:0.35rem;"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="pulse-pill"><span class="pulse-icon" id="pv-pulse-icon">{_pulse_icon}</span>'
        f'<div class="pulse-meta"><span class="pulse-lbl">Productivity Pulse</span>'
        f'<span class="pulse-val">{avg_health}% Healthy</span></div></div>',
        unsafe_allow_html=True,
    )

# Client-side: rewrite greeting to reflect user's actual local time
_first_safe = _first.replace("'", "\\'")
st.markdown(f"""<script>
(function() {{
    const update = () => {{
        const doc = window.parent.document;
        const g = doc.getElementById('pv-greeting');
        const m = doc.getElementById('pv-micro');
        const p = doc.getElementById('pv-pulse-icon');
        if (!g || !m) {{ setTimeout(update, 200); return; }}
        const h = new Date().getHours();
        let greet, micros, icon;
        if (h < 5)        {{ greet = "Still up, {_first_safe}?";              micros = ["Night owl spotted. The best ideas come after midnight.", "Not kept working late nights, I see.", "The world's asleep — this is your edge.", "Late nights and big dreams. Respect."]; icon = "🌙"; }}
        else if (h < 12)  {{ greet = "Good morning, {_first_safe}";           micros = ["Early start. Your projects are grateful.", "Fresh day, fresh momentum. Let's go.", "The best builders start before the world wakes up.", "Morning clarity is a superpower. Use it."]; icon = "☀️"; }}
        else if (h < 17)  {{ greet = "Good afternoon, {_first_safe}";         micros = ["Deep work hours. Make them count.", "Every update brings you closer to launch.", "Clarity builds momentum. Keep going.", "Your work is tracked, your progress is real."]; icon = "🌤️"; }}
        else if (h < 21)  {{ greet = "Good evening, {_first_safe}";           micros = ["Wrapping up strong. Log your wins.", "End of day check-in. How did it go?", "Evening reflection fuels tomorrow.", "The best teams review before they rest."]; icon = "🌆"; }}
        else              {{ greet = "Burning the midnight oil, {_first_safe}?"; micros = ["Late night mode. The quiet hours hit different.", "Still here? Your projects appreciate the dedication.", "Night shifts build empires.", "Almost tomorrow. Make this session count."]; icon = "🌙"; }}
        g.textContent = greet;
        m.textContent = micros[h % micros.length];
        if (p) p.textContent = icon;
    }};
    update();
}})();
</script>""", unsafe_allow_html=True)

# Modals
if st.session_state.get("show_new_project_modal"):
    st.markdown('<div class="pv-section-hdr">Create New Project</div>', unsafe_allow_html=True)
    with st.container():
        with st.form("new_project_form"):
            proj_title    = st.text_input("Project Name *", placeholder="e.g. Auth Infrastructure Rewrite")
            proj_desc     = st.text_area("Description", placeholder="What is this project about?", height=70)
            proj_tags_raw = st.text_input("Tags (comma-separated)", placeholder="design, strategy, api")
            cs, cc = st.columns(2)
            submitted = cs.form_submit_button("Create Project", type="primary", use_container_width=True)
            cancelled = cc.form_submit_button("Cancel", use_container_width=True)
        if submitted:
            if not proj_title.strip(): st.error("Project name is required.")
            else:
                tags = [t.strip() for t in proj_tags_raw.split(",") if t.strip()]
                project = create_project(user["id"], proj_title.strip(), proj_desc.strip(), tags)
                st.session_state["show_new_project_modal"] = False
                st.session_state["current_project"] = project["id"]
                st.switch_page("pages/3_project.py")
        if cancelled:
            st.session_state["show_new_project_modal"] = False
            st.rerun()

if st.session_state.get("show_import_modal"):
    st.markdown('<div class="pv-section-hdr">Import Existing Project</div>', unsafe_allow_html=True)
    with st.container():
        render_import_modal(user)

st.markdown('<div style="height:1px;background:rgba(142,94,78,0.08);margin:0.75rem 0 1.25rem;"></div>', unsafe_allow_html=True)

if not projects:
    st.markdown("""<div class="empty-state" style="padding:5rem 2rem;">
        <h3>No projects yet</h3>
        <p>Create your first project to start tracking progress with AI health scores and automated snapshots.</p>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Colour helpers ─────────────────────────────────────────────────────────────
STATUS_DOT  = {"active": "#E07060", "paused": "#C4A882", "completed": "#8E5E4E", "archived": "#A88F87"}
STATUS_TXT  = {"active": ("#E07060","Active"), "paused": ("#C4A882","Paused"), "completed": ("#8E5E4E","Completed"), "archived": ("#A88F87","Archived")}
UPD_CLR     = {"note": "#E07060", "decision": "#8E5E4E", "milestone": "#C4A882", "blocker": "#CF6F61", "pivot": "#F5C4B4"}

def _hclr(h):
    return "#8E5E4E" if h >= 70 else ("#C4A882" if h >= 40 else "#CF6F61")

# ── Main 3-column layout ───────────────────────────────────────────────────────
col_feat, col_energy, col_focus = st.columns([4, 5, 4], gap="medium")

# ─── Featured: all active projects as cards ────────────────────────────────────
with col_feat:
    GRAD_STOPS = {
        "active":    [("E88D7D","C4A882"), ("D4543F","E88D7D"), ("C4A882","E07060")],
        "paused":    [("C4A882","F5C4B4")],
        "completed": [("8E5E4E","C4A882")],
        "archived":  [("A88F87","FFF0EB")],
    }
    active_projects = sorted(
        [p for p in projects if p.get("status") == "active"],
        key=lambda p: -(p.get("health_score") or 0)
    )
    # Fall back to first project if none active
    if not active_projects:
        active_projects = projects[:1]

    st.markdown(
        f'<div class="sec-lbl">Featured · {len(active_projects)} Active</div>',
        unsafe_allow_html=True,
    )

    for _fi, fp in enumerate(active_projects):
        fp_health = fp.get("health_score") or 0
        fp_status = fp.get("status", "active")
        fp_title  = _html.escape(_clean(fp.get("title") or "Untitled"))
        fp_desc   = _html.escape(clean_description(_clean(fp.get("description") or ""))[:90] or "No description yet.")
        fp_tags   = fp.get("tags") or []
        fp_tag1   = _html.escape(_clean(fp_tags[0])).upper() if fp_tags else "ACTIVE"
        fp_pid    = fp["id"]
        fp_bclr   = _hclr(fp_health)
        _grads    = GRAD_STOPS.get(fp_status, [("E88D7D","C4A882")])
        g1, g2    = _grads[_fi % len(_grads)]

        st.markdown(
            f'<div class="feat-card">'
            f'<div class="feat-visual" style="background:linear-gradient(135deg,#{g1} 0%,#{g2} 100%);">'
            f'<span class="feat-badge">{fp_tag1}</span>'
            f'</div>'
            f'<div class="feat-body">'
            f'<div class="feat-title">{fp_title}</div>'
            f'<div class="feat-desc">{fp_desc}</div>'
            f'<div class="feat-prog-lbl"><span>PROGRESS</span><span style="color:{fp_bclr};">{fp_health}%</span></div>'
            f'<div class="feat-prog-wrap"><div class="feat-prog-bar" style="width:{fp_health}%;"></div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("View Project →", key=f"feat_open_{fp_pid}", use_container_width=True, type="primary"):
            st.session_state["current_project"] = fp_pid
            st.switch_page("pages/3_project.py")

# ─── All Projects ──────────────────────────────────────────────────────────────
with col_energy:
    active_projects = [p for p in projects if p.get("status") == "active"]
    other_projects  = [p for p in projects if p.get("status") != "active"]
    all_sorted = (
        sorted(active_projects, key=lambda p: -(p.get("health_score") or 0))
        + sorted(other_projects, key=lambda p: -(p.get("health_score") or 0))
    )
    total_cnt   = len(projects)
    active_cnt  = len(active_projects)
    completed_cnt = sum(1 for p in projects if p.get("status") == "completed")
    paused_cnt    = sum(1 for p in projects if p.get("status") == "paused")
    st.markdown(
        f'<div class="sec-lbl">All Projects'
        f'<span style="margin-left:0.5rem;font-size:0.55rem;background:rgba(224,112,96,0.12);'
        f'color:#E07060;border-radius:999px;padding:1px 7px;font-weight:700;">'
        f'{total_cnt} total</span></div>',
        unsafe_allow_html=True,
    )

    # Quick stats summary at top of column to fill vertical space
    st.markdown(
        f'<div style="display:flex;gap:0.5rem;margin-bottom:0.75rem;">'
        f'<div style="flex:1;background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);'
        f'border-radius:10px;padding:0.55rem 0.75rem;text-align:center;">'
        f'<div style="font-size:1.1rem;font-weight:700;color:#E07060;line-height:1;">{active_cnt}</div>'
        f'<div style="font-size:0.55rem;color:#A88F87;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-top:2px;">Active</div>'
        f'</div>'
        f'<div style="flex:1;background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);'
        f'border-radius:10px;padding:0.55rem 0.75rem;text-align:center;">'
        f'<div style="font-size:1.1rem;font-weight:700;color:#8E5E4E;line-height:1;">{completed_cnt}</div>'
        f'<div style="font-size:0.55rem;color:#A88F87;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-top:2px;">Completed</div>'
        f'</div>'
        f'<div style="flex:1;background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);'
        f'border-radius:10px;padding:0.55rem 0.75rem;text-align:center;">'
        f'<div style="font-size:1.1rem;font-weight:700;color:#C4A882;line-height:1;">{paused_cnt}</div>'
        f'<div style="font-size:0.55rem;color:#A88F87;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-top:2px;">Paused</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for project in all_sorted:
        health    = project.get("health_score") or 0
        status    = project.get("status", "active")
        pid       = project["id"]
        tags      = project.get("tags") or []
        updated   = relative_time(project.get("updated_at", ""))
        dot_clr   = STATUS_DOT.get(status, "#A88F87")
        s_clr, s_lbl = STATUS_TXT.get(status, ("#A88F87", status.capitalize()))
        h_clr     = _hclr(health)
        title_s   = _html.escape(_clean(project.get("title") or "Untitled"))
        tag_pills = "".join(f'<span class="proj-row-tag">{_html.escape(_clean(t))}</span>' for t in tags[:3])
        tag_row   = f'<div class="proj-row-tags">{tag_pills}</div>' if tags else ""

        _c_row, _c_btn = st.columns([10, 2])
        with _c_row:
            st.markdown(
                f'<div class="proj-row">'
                f'<div class="proj-row-left">'
                f'<div class="proj-row-name">{title_s}</div>'
                f'<div class="proj-row-meta">'
                f'<span class="proj-row-dot" style="background:{dot_clr};"></span>'
                f'<span class="proj-row-status" style="color:{s_clr};">{s_lbl}</span>'
                f'<span style="color:rgba(142,94,78,0.2);font-size:0.7rem;margin:0 2px;">·</span>'
                f'<span class="proj-row-time">{updated}</span>'
                f'</div>'
                f'{tag_row}'
                f'</div>'
                f'<div class="proj-row-right">'
                f'<div class="proj-row-score" style="color:{h_clr};">{health}</div>'
                f'<div class="proj-prog-wrap"><div class="proj-prog-fill" style="width:{health}%;background:{h_clr};"></div></div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with _c_btn:
            st.markdown('<div style="height:0.55rem;"></div>', unsafe_allow_html=True)
            if st.button("→", key=f"open_{pid}", use_container_width=True):
                st.session_state["current_project"] = pid
                st.switch_page("pages/3_project.py")

# ─── Daily Focus ──────────────────────────────────────────────────────────────
with col_focus:
    st.markdown('<div class="sec-lbl">Daily Focus</div>', unsafe_allow_html=True)

    def _focus_row(u):
        utype    = u.get("update_type", "note")
        dot_clr  = UPD_CLR.get(utype, "#E07060")
        raw      = _clean(u.get("content") or u.get("ai_summary") or "")
        text     = _html.escape(raw[:70] + "…" if len(raw) > 70 else raw)
        proj     = _html.escape(project_map.get(u.get("project_id", ""), ""))
        when     = _html.escape(relative_time(u.get("created_at", "")))
        done     = utype in ("milestone", "decision")
        ring_cls = "focus-ring focus-ring-done" if done else "focus-ring"
        chk      = '<span class="focus-check">✓</span>' if done else ""
        dot_span = f'<span style="display:inline-block;width:4px;height:4px;border-radius:50%;background:{dot_clr};vertical-align:middle;margin-right:3px;"></span>'
        return (
            f'<div class="focus-row">'
            f'<div class="{ring_cls}">{chk}</div>'
            f'<div class="focus-body">'
            f'<div class="focus-text">{dot_span}{text}</div>'
            f'<div class="focus-proj">{proj}</div>'
            f'</div>'
            f'<div class="focus-time">{when}</div>'
            f'</div>'
        )

    rows = "".join(_focus_row(u) for u in recent_updates[:10])
    empty = '<div style="text-align:center;padding:1.5rem 0;color:#A88F87;font-size:0.8rem;">No activity yet.</div>'
    st.markdown(
        f'<div class="focus-card"><div class="focus-hdr">Recent Activity</div>{rows or empty}</div>',
        unsafe_allow_html=True,
    )

# ── Bottom row — Timeline + Stats ──────────────────────────────────────────────
st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

# ── Bottom — Timeline full width ───────────────────────────────────────────────
tl_items = (milestones or recent_updates)[:6]
NODE_COLORS = ["#E07060", "#C4A882", "#8E5E4E", "#F5C4B4", "#CF6F61", "#E07060"]

def _tl_node(item, clr, is_last):
    name = _html.escape(_clean(item.get("content") or item.get("title") or ""))
    name = name[:55] + "…" if len(name) > 55 else name
    proj = _html.escape(project_map.get(item.get("project_id", ""), ""))
    when = _html.escape(relative_time(item.get("created_at", "")))
    dash = "" if is_last else '<div class="tl-dash"></div>'
    return (
        f'<div class="tl-node">'
        f'<div class="tl-dot-col"><div class="tl-dot" style="background:{clr};"></div>{dash}</div>'
        f'<div><div class="tl-when" style="color:{clr};">{when}</div>'
        f'<div class="tl-name">{name}</div>'
        f'<div class="tl-detail">{proj}</div></div>'
        f'</div>'
    )

nodes = "".join(
    _tl_node(item, NODE_COLORS[i % len(NODE_COLORS)], i == len(tl_items) - 1)
    for i, item in enumerate(tl_items)
)
no_tl = '<div style="text-align:center;padding:1rem 0;color:#A88F87;font-size:0.8rem;">No milestones yet.</div>'
total_m = len(milestones)
st.markdown(
    f'<div class="tl-section">'
    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.1rem;">'
    f'<div class="tl-hdr" style="margin-bottom:0;">Timeline Highlights</div>'
    f'<div style="display:flex;gap:1.5rem;">'
    f'<div style="text-align:center;">'
    f'<div class="stat-lbl">TOTAL PROJECTS</div><div class="stat-num" style="font-size:1.5rem;">{len(projects)}</div>'
    f'</div>'
    f'<div style="width:1px;background:rgba(142,94,78,0.12);"></div>'
    f'<div style="text-align:center;">'
    f'<div class="stat-lbl">MILESTONES</div><div class="stat-num" style="font-size:1.5rem;">{total_m}/{max(total_updates,1)}</div>'
    f'</div>'
    f'</div>'
    f'</div>'
    f'<div class="tl-nodes">{nodes or no_tl}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
