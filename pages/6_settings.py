import os
import html as _html
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Settings",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth, logout
from utils.sidebar import render_sidebar
from services.auth_service import get_supabase, get_supabase_admin
from services import ai_service as ai
from services import db_service as db

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""<style>
/* ── Settings input overrides ─────────────────── */
div[data-baseweb="input"] > div {
    background:    #FFFFFF !important;
    border:        1px solid rgba(142,94,78,0.18) !important;
    border-radius: 10px !important;
}
div[data-baseweb="input"] > div:focus-within {
    border-color: #E88D7D !important;
    box-shadow:   0 0 0 3px rgba(232,141,125,0.1) !important;
}
div[data-baseweb="input"] input {
    color:     #2C1810 !important;
    font-size: 0.875rem !important;
}
div[data-baseweb="input"] input::placeholder {
    color: #A88F87 !important;
}
/* Password field eye icon */
div[data-testid="stTextInput"] button {
    color: #A88F87 !important;
    background: transparent !important;
    border: none !important;
}
div[data-testid="stTextInput"] button:hover {
    color: #2C1810 !important;
}
/* Settings form card */
div[data-testid="stForm"] {
    background:    #FFFFFF !important;
    border:        1px solid rgba(142,94,78,0.1) !important;
    border-radius: 16px !important;
    padding:       1.5rem !important;
    box-shadow:    0 1px 4px rgba(142,94,78,0.06) !important;
}
/* Status indicator rows */
.pv-status-row {
    display:       flex;
    align-items:   center;
    gap:           0.75rem;
    padding:       0.6rem 0;
    border-bottom: 1px solid rgba(142,94,78,0.12);
    font-size:     0.875rem;
}
.pv-status-row:last-child { border-bottom: none; }
.pv-status-dot {
    width:         7px;
    height:        7px;
    border-radius: 50%;
    flex-shrink:   0;
}
.pv-status-label { color: #2C1810; font-weight: 500; flex: 1; }
.pv-status-detail { color: #A88F87; font-size: 0.78rem; }
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user
_all_proj = db.get_projects_for_user(user["id"])
render_sidebar(user, active="settings", projects=_all_proj)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:2rem;">
    <h2 style="margin:0 0 0.3rem;font-size:1.75rem;font-weight:700;color:#2C1810;line-height:1.2;">Account Settings</h2>
    <p style="color:#A88F87;font-size:0.8125rem;margin:0;">Manage your profile, API keys, and preferences.</p>
</div>
""", unsafe_allow_html=True)

# ── Layout: two-column with max width ─────────────────────────────────────────
col_main, col_right = st.columns([2, 1])

with col_main:
    # ── Profile ────────────────────────────────────────────────────────────────
    st.markdown('<div class="pv-section-hdr">Profile</div>', unsafe_allow_html=True)
    with st.form("profile_form"):
        display_name = st.text_input("Display Name", value=user.get("name", ""), placeholder="Your name")
        st.text_input("Email", value=user.get("email", ""), disabled=True)
        save_profile = st.form_submit_button("Save Profile", type="primary")

    if save_profile:
        if display_name.strip():
            get_supabase_admin().table("users").update(
                {"name": display_name.strip()}
            ).eq("id", user["id"]).execute()
            st.session_state.user["name"] = display_name.strip()
            st.toast("Profile saved")
        else:
            st.markdown(
                '<p style="color:#CF6F61;font-size:0.8rem;margin-top:0.5rem;">Name cannot be empty.</p>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

    # ── API Keys ───────────────────────────────────────────────────────────────
    st.markdown('<div class="pv-section-hdr">API Keys</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#A88F87;font-size:0.8rem;margin:0 0 1rem;">Keys are stored in your browser session only and reset on sign-out.</p>',
        unsafe_allow_html=True,
    )
    with st.form("api_keys_form"):
        groq_key    = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
        openai_key  = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        gh_token    = st.text_input("GitHub Personal Access Token", type="password", placeholder="ghp_...")
        save_keys   = st.form_submit_button("Save API Keys", type="primary")

    if save_keys:
        if groq_key:
            st.session_state["groq_key"] = groq_key
        if openai_key:
            st.session_state["openai_key"] = openai_key
        if gh_token:
            st.session_state["github_token"] = gh_token
        if any([groq_key, openai_key, gh_token]):
            st.toast("API keys saved to session")
        else:
            st.markdown(
                '<p style="color:#7A6560;font-size:0.8rem;margin-top:0.5rem;">No keys entered.</p>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

    # ── Weekly Digest ──────────────────────────────────────────────────────────
    st.markdown('<div class="pv-section-hdr">Weekly Email Digest</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#7A6560;font-size:0.8rem;margin:0 0 0.75rem;">Receive a Monday morning summary of your project portfolio.</p>',
        unsafe_allow_html=True,
    )
    try:
        _admin_s = get_supabase_admin()
        _rows = _admin_s.table("users").select("digest_enabled").eq("id", user["id"]).limit(1).execute().data
        user_row = _rows[0] if _rows else {}
        digest_currently_on = user_row.get("digest_enabled", True)
        digest_on = st.toggle("Enable weekly digest", value=digest_currently_on)
        if digest_on != digest_currently_on:
            _admin_s.table("users").update({"digest_enabled": digest_on}).eq("id", user["id"]).execute()
            st.toast("Preference saved")
    except Exception as _e:
        st.markdown(
            f'<p style="color:#7A6560;font-size:0.8rem;">Could not load digest setting: {_html.escape(str(_e)[:80])}</p>',
            unsafe_allow_html=True,
        )

with col_right:
    # ── API Status ─────────────────────────────────────────────────────────────
    st.markdown('<div class="pv-section-hdr">API Status</div>', unsafe_allow_html=True)

    if st.button("Check Connections", use_container_width=True, key="check_api_status"):
        with st.spinner("Testing..."):
            statuses = ai.check_provider_status()

        try:
            get_supabase_admin().table("users").select("id").limit(1).execute()
            statuses["supabase"] = {"ok": True, "label": "Supabase", "detail": "Connected"}
        except Exception as e:
            statuses["supabase"] = {"ok": False, "label": "Supabase", "detail": str(e)[:60]}

        rows_html = ""
        for key in ["supabase", "groq", "openai"]:
            s = statuses.get(key)
            if not s:
                continue
            dot_clr = "#E88D7D" if s["ok"] else "#CF6F61"
            label   = _html.escape(s["label"])
            detail  = _html.escape(s["detail"][:60])
            rows_html += f"""
            <div class="pv-status-row">
                <span class="pv-status-dot" style="background:{dot_clr};"></span>
                <span class="pv-status-label">{label}</span>
                <span class="pv-status-detail">{detail}</span>
            </div>
            """
        if rows_html:
            st.markdown(
                f'<div style="background:#FFFFFF;border:1px solid rgba(142,94,78,0.12);border-radius:8px;padding:0.75rem 1rem;margin-top:0.5rem;">{rows_html}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

    # ── Danger Zone ────────────────────────────────────────────────────────────
    st.markdown('<div class="pv-section-hdr">Danger Zone</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#A88F87;font-size:0.78rem;margin:0 0 0.6rem;">This will end all active sessions on every device.</p>',
        unsafe_allow_html=True,
    )
    if st.button("Sign Out Everywhere", type="primary", use_container_width=True, key="signout_everywhere"):
        logout()
        st.switch_page("pages/1_login.py")
