import streamlit as st
from services.auth_service import sign_out


def render_sidebar(active_page: str = "dashboard"):
    user = st.session_state.get("user", {})
    with st.sidebar:
        st.markdown('<div class="pv-brand">🔐 ProjectVault</div>', unsafe_allow_html=True)
        if user:
            st.markdown(f"<small style='color:#666666'>Signed in as **{user.get('name', user.get('email', ''))}**</small>", unsafe_allow_html=True)
        st.divider()
        st.page_link("pages/2_dashboard.py", label="Dashboard", icon="🏠")
        st.page_link("pages/4_search.py", label="Search", icon="🔍")
        st.page_link("pages/6_settings.py", label="Settings", icon="⚙️")
        st.divider()
        if st.button("Sign Out", use_container_width=True, key="navbar_signout"):
            sign_out()
            st.switch_page("pages/1_login.py")
