from __future__ import annotations
import os
import re
import html as _html
import streamlit as st
from utils.session import logout

# ── Vault Logo SVG ─────────────────────────────────────────────────────────────
LOGO_SVG = (
    '<svg width="38" height="38" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">'
    # Vault circle body (dark interior)
    '<circle cx="18" cy="15" r="11" fill="#2C1810"/>'
    # Vault door panel (open, left side)
    '<rect x="2" y="7" width="8" height="16" rx="2.5" fill="#D4543F"/>'
    # Door right edge shadow
    '<rect x="9" y="7" width="1.5" height="16" rx="0.5" fill="#B03D2E"/>'
    # Combination lock dial
    '<circle cx="6" cy="15" r="3.2" fill="#C04535"/>'
    '<circle cx="6" cy="15" r="2" fill="#FFE4D8" opacity="0.55"/>'
    '<circle cx="6" cy="15" r="0.9" fill="#D4543F"/>'
    # Bar chart floor line
    '<line x1="12.5" y1="22" x2="27" y2="22" stroke="#4A2820" stroke-width="0.8"/>'
    # Bar charts (coral, sand, terracotta, peach)
    '<rect x="13" y="19" width="2" height="3" rx="0.4" fill="#E88D7D"/>'
    '<rect x="16.5" y="16" width="2" height="6" rx="0.4" fill="#C4A882"/>'
    '<rect x="20" y="17.5" width="2" height="4.5" rx="0.4" fill="#E07060"/>'
    '<rect x="23.5" y="14.5" width="2" height="7.5" rx="0.4" fill="#8E5E4E"/>'
    # Gear outline (top-right interior)
    '<circle cx="21.5" cy="10" r="3" fill="none" stroke="#C4A882" stroke-width="1.4"/>'
    '<circle cx="21.5" cy="10" r="1.2" fill="#C4A882"/>'
    # Gear spokes
    '<line x1="21.5" y1="6.6" x2="21.5" y2="7.8" stroke="#C4A882" stroke-width="1.3" stroke-linecap="round"/>'
    '<line x1="21.5" y1="12.2" x2="21.5" y2="13.4" stroke="#C4A882" stroke-width="1.3" stroke-linecap="round"/>'
    '<line x1="18.1" y1="10" x2="19.3" y2="10" stroke="#C4A882" stroke-width="1.3" stroke-linecap="round"/>'
    '<line x1="23.7" y1="10" x2="24.9" y2="10" stroke="#C4A882" stroke-width="1.3" stroke-linecap="round"/>'
    '</svg>'
)

_clean = lambda t: re.sub(r'<[^>]+>', '', _html.unescape(str(t or ''))).strip()


def _nav(label: str, page_id: str, active: str, page_path: str, key: str) -> None:
    if active == page_id:
        st.markdown(f'<div class="pv-nav-active">{label}</div>', unsafe_allow_html=True)
    else:
        if st.button(label, key=key, use_container_width=True):
            st.switch_page(page_path)


def _import_btn(active: str) -> None:
    if st.button("Import", key="sb_import", use_container_width=True):
        st.session_state["show_import_modal"] = True
        st.session_state["show_new_project_modal"] = False
        if active != "dashboard":
            st.switch_page("pages/2_dashboard.py")
    if st.button("New Project", key="sb_newproj", use_container_width=True):
        st.session_state["show_new_project_modal"] = True
        st.session_state["show_import_modal"] = False
        if active != "dashboard":
            st.switch_page("pages/2_dashboard.py")


def _invite_section(user: dict, projects: list | None) -> None:
    _show = st.session_state.get("show_invite_links", False)
    if st.button("+ Invite Member", key="sb_invite", use_container_width=True, type="primary"):
        st.session_state["show_invite_links"] = not _show

    if st.session_state.get("show_invite_links"):
        _app_url = os.getenv("APP_URL", "http://localhost:8501")
        items = [p for p in (projects or []) if p.get("share_token")]
        if items:
            st.markdown('<div style="height:0.35rem;"></div>', unsafe_allow_html=True)
            for p in items[:6]:
                ptitle = _clean(p.get("title", "Project"))[:22]
                link = f"{_app_url}/shared_project?share={p['share_token']}"
                st.markdown(
                    f'<div class="sb-share-box">'
                    f'<div class="sb-share-proj">{_html.escape(ptitle)}</div>'
                    f'<div class="sb-share-link">{_html.escape(link)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="font-size:0.75rem;color:#A88F87;padding:0.5rem 0.8rem;">No shareable projects found.</div>',
                unsafe_allow_html=True,
            )


def render_sidebar(user: dict, active: str = "dashboard", projects: list | None = None) -> None:
    _subtitle_map = {
        "dashboard": "Member", "team": "Team", "schedule": "Schedule",
        "archive": "Archive", "help": "Help & Support",
        "settings": "Settings", "ai": "AI Assistant", "search": "Search",
    }
    _initials = "".join(n[0].upper() for n in (user.get("name") or "U").split()[:2])
    _name_safe = _html.escape(user.get("name") or "")
    subtitle   = _subtitle_map.get(active, "ProjectVault")

    with st.sidebar:
        # Force left-align on all sidebar buttons (overrides Streamlit defaults)
        st.markdown("""<style>
[data-testid="stSidebar"] div.stButton > button {
    text-align: left !important; justify-content: flex-start !important;
}
[data-testid="stSidebar"] div.stButton > button > div,
[data-testid="stSidebar"] div.stButton > button > div > p {
    text-align: left !important; width: 100% !important; margin: 0 !important;
    font-size: 0.84rem !important; line-height: 1.4 !important;
}
[data-testid="stSidebar"] div.stButton,
[data-testid="stSidebar"] div.stMarkdown,
[data-testid="stSidebar"] div.element-container {
    margin: 0 !important; padding-top: 0 !important; padding-bottom: 0 !important;
}
</style>""", unsafe_allow_html=True)

        # Brand
        st.markdown(
            f'<div class="pv-wordmark">{LOGO_SVG}<span style="margin-left:4px;">ProjectVault</span></div>',
            unsafe_allow_html=True,
        )
        # User card
        st.markdown(
            f'<div class="pv-user-card">'
            f'<div class="pv-avatar-v2">{_initials}</div>'
            f'<div style="min-width:0;">'
            f'<div class="pv-user-name">{_name_safe}</div>'
            f'<div class="pv-user-role">{subtitle} · ProjectVault</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── Main ──────────────────────────────────────────────────────────
        st.markdown('<div class="sb-lbl">Main</div>', unsafe_allow_html=True)
        _nav("Dashboard",   "dashboard", active, "pages/2_dashboard.py",    "sb_dash")
        _nav("Team",        "team",      active, "pages/10_team.py",         "sb_team")
        _nav("Schedule",    "schedule",  active, "pages/11_schedule.py",     "sb_sched")

        # ── Tools ─────────────────────────────────────────────────────────
        st.markdown('<div class="sb-lbl">Tools</div>', unsafe_allow_html=True)
        _import_btn(active)
        _nav("AI Assistant", "ai",      active, "pages/7_portfolio_chat.py", "sb_ai")

        # ── Account ───────────────────────────────────────────────────────
        st.markdown('<div class="sb-lbl">Account</div>', unsafe_allow_html=True)
        _nav("Settings",  "settings", active, "pages/6_settings.py",  "sb_settings")
        _nav("Archive",   "archive",  active, "pages/8_archive.py",   "sb_archive")
        _nav("Help",      "help",     active, "pages/9_help.py",      "sb_help")

        st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
        _invite_section(user, projects)
        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        st.divider()
        if st.button("Sign out", key="sb_signout", use_container_width=True):
            logout()
