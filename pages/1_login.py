import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Sign In",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import handle_login, handle_signup
from utils.session import save_session_to_browser

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
.stApp { background: #FFF8F5; }
.block-container { padding-top: 2.5rem !important; }

div[data-testid="stForm"] {
    background:    #FFFFFF !important;
    border:        1px solid rgba(142,94,78,0.12) !important;
    border-radius: 20px !important;
    padding:       1.75rem !important;
    box-shadow:    0 2px 12px rgba(142,94,78,0.08) !important;
}
div[data-baseweb="input"] > div {
    background:    #FFFFFF !important;
    border:        1px solid rgba(142,94,78,0.18) !important;
    border-radius: 10px !important;
}
div[data-baseweb="input"] > div:focus-within {
    border-color: #E88D7D !important;
    box-shadow:   0 0 0 3px rgba(232,141,125,0.12) !important;
}
div[data-baseweb="input"] input {
    background: #FFFFFF !important;
    color:      #2C1810 !important;
    font-size:  0.875rem !important;
}
div[data-baseweb="input"] input::placeholder { color: #A88F87 !important; }
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {
    -webkit-box-shadow:      0 0 0 30px #FFFFFF inset !important;
    -webkit-text-fill-color: #2C1810 !important;
    caret-color:             #2C1810 !important;
    border:                  1px solid rgba(142,94,78,0.18) !important;
    transition:              background-color 5000s ease-in-out 0s;
}
.stTabs [data-baseweb="tab-list"] {
    background: #FFF0EB !important;
    border: 1px solid rgba(142,94,78,0.1) !important;
}
</style>
""", unsafe_allow_html=True)

# Already logged in
if st.session_state.get("user"):
    st.switch_page("pages/2_dashboard.py")

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 2.5rem 0 2rem;">
    <div style="
        font-size: 3.2rem;
        font-weight: 700;
        color: #2C1810;
        letter-spacing: -2px;
        line-height: 1.05;
        margin-bottom: 0.75rem;
    ">ProjectVault</div>
    <p style="color:#6B4A3E; font-size:1.05rem; line-height:1.6; margin:0 auto; max-width:380px;">
        Your AI-powered project memory.<br>
        <span style="color:#A88F87; font-size:0.9rem;">Track progress, capture decisions, and learn from every project.</span>
    </p>
    <div style="margin-top:1.5rem; display:flex; flex-wrap:wrap; justify-content:center; gap:5px;">
        <span class="feature-pill">AI Health Scores</span>
        <span class="feature-pill">Smart Snapshots</span>
        <span class="feature-pill">Semantic Search</span>
        <span class="feature-pill">Team Insights</span>
        <span class="feature-pill">Deep Analysis</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ────────────────────────────────────────────────────────────────────────
tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

with tab_login:
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

    if submitted:
        if not email or not password:
            st.markdown(
                '<p style="color:#CF6F61;font-size:0.8rem;margin-top:0.5rem;">Please enter your email and password.</p>',
                unsafe_allow_html=True,
            )
        else:
            with st.spinner("Signing in..."):
                success, error = handle_login(email.strip(), password)
            if success:
                at = st.session_state.get("access_token", "")
                rt = st.session_state.get("refresh_token", "")
                if at:
                    save_session_to_browser(at, rt)
                st.switch_page("pages/2_dashboard.py")
            else:
                st.markdown(
                    f'<p style="color:#CF6F61;font-size:0.8rem;margin-top:0.5rem;">{error}</p>',
                    unsafe_allow_html=True,
                )

with tab_signup:
    with st.form("signup_form", clear_on_submit=False):
        name = st.text_input("Full Name", placeholder="Jane Doe")
        email_s = st.text_input("Email", placeholder="you@example.com")
        password_s = st.text_input("Password", type="password", placeholder="Min 6 characters")
        submitted_s = st.form_submit_button("Create Account", use_container_width=True, type="primary")

    if submitted_s:
        if not name or not email_s or not password_s:
            st.markdown(
                '<p style="color:#CF6F61;font-size:0.8rem;margin-top:0.5rem;">All fields are required.</p>',
                unsafe_allow_html=True,
            )
        elif len(password_s) < 6:
            st.markdown(
                '<p style="color:#CF6F61;font-size:0.8rem;margin-top:0.5rem;">Password must be at least 6 characters.</p>',
                unsafe_allow_html=True,
            )
        else:
            with st.spinner("Creating your account..."):
                success, error = handle_signup(email_s.strip(), password_s, name.strip())
            if success:
                if st.session_state.get("user"):
                    st.switch_page("app.py")
                else:
                    st.markdown(
                        '<p style="color:#E88D7D;font-size:0.8rem;margin-top:0.5rem;">Account created! You can sign in now.</p>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f'<p style="color:#CF6F61;font-size:0.8rem;margin-top:0.5rem;">{error}</p>',
                    unsafe_allow_html=True,
                )

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; margin-top:2.5rem; padding-top:1.5rem; border-top:1px solid #c8ddd5;">
    <p style="color:#A88F87; font-size:0.78rem; margin:0;">
        Built with <span style="color:#2C1810; font-weight:500;">Groq AI</span>
        · Powered by <span style="color:#A88F87; font-weight:500;">Supabase</span>
    </p>
</div>
""", unsafe_allow_html=True)
