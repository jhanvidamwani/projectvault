import os
import json
import html as _html
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Help",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth
from utils.sidebar import render_sidebar
from services.auth_service import get_supabase_admin
from services import db_service as db

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""<style>
.help-cat-card {
    background: #FFFFFF; border: 1px solid rgba(142,94,78,0.18);
    border-radius: 16px; padding: 1.1rem 1.25rem; margin-bottom: 0.55rem;
    box-shadow: 0 2px 8px rgba(142,94,78,0.07); cursor: default;
}
.help-cat-icon { font-size: 1.4rem; margin-bottom: 0.4rem; }
.help-cat-title { font-size: 0.88rem; font-weight: 700; color: #2C1810; margin-bottom: 0.25rem; }
.help-cat-desc  { font-size: 0.78rem; color: #7A6560; line-height: 1.55; }
.help-faq { background: #FFFFFF; border: 1px solid rgba(142,94,78,0.15); border-radius: 12px;
            padding: 0.9rem 1.1rem; margin-bottom: 0.4rem; }
.help-faq-q { font-size: 0.85rem; font-weight: 600; color: #2C1810; margin-bottom: 0.35rem; }
.help-faq-a { font-size: 0.8rem; color: #7A6560; line-height: 1.6; }
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user
all_projects = db.get_projects_for_user(user["id"])
render_sidebar(user, active="help", projects=all_projects)


def _save_request(subject: str, category: str, message: str) -> bool:
    payload = {
        "user_id":    user["id"],
        "user_email": user.get("email", ""),
        "user_name":  user.get("name", ""),
        "subject":    subject,
        "category":   category,
        "message":    message,
        "status":     "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # Try Supabase first
    try:
        get_supabase_admin().table("support_requests").insert(payload).execute()
        return True
    except Exception:
        pass
    # Fallback: local file
    try:
        log = Path(__file__).parent.parent / "data" / "support_requests.json"
        log.parent.mkdir(exist_ok=True)
        existing = json.loads(log.read_text()) if log.exists() else []
        existing.append(payload)
        log.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:2rem;">
    <h2 style="margin:0 0 0.3rem;font-size:1.75rem;font-weight:700;color:#2C1810;line-height:1.2;">Help & Support</h2>
    <p style="color:#7A6560;font-size:0.8125rem;margin:0;">Get help, report a bug, or share feedback with the ProjectVault team.</p>
</div>
""", unsafe_allow_html=True)

col_form, col_info = st.columns([3, 2], gap="large")

with col_form:
    st.markdown('<div class="pv-section-hdr">Send a Support Request</div>', unsafe_allow_html=True)
    with st.form("help_form", clear_on_submit=True):
        category = st.selectbox(
            "Category",
            ["Bug Report", "Feature Request", "Account Issue", "Data / Import Question", "General Question", "Other"],
        )
        subject = st.text_input("Subject", placeholder="Short summary of your request")
        message = st.text_area(
            "Message",
            placeholder="Describe your issue or request in detail. Include any steps to reproduce bugs.",
            height=150,
        )
        submitted = st.form_submit_button("Send Request", type="primary", use_container_width=True)

    if submitted:
        if not subject.strip() or not message.strip():
            st.markdown(
                '<p style="color:#CF6F61;font-size:0.8rem;margin-top:0.5rem;">Please fill in both subject and message.</p>',
                unsafe_allow_html=True,
            )
        else:
            ok = _save_request(subject.strip(), category, message.strip())
            if ok:
                st.markdown(
                    '<div style="background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);border-left:3px solid #8E5E4E;border-radius:12px;padding:1rem 1.25rem;margin-top:1rem;">'
                    '<div style="font-size:0.88rem;font-weight:700;color:#2C1810;margin-bottom:0.3rem;">Request received</div>'
                    '<div style="font-size:0.8rem;color:#7A6560;line-height:1.6;">Your support request has been submitted. The ProjectVault team will review it and follow up within 1–2 business days.</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.error("Could not save your request. Please try again later.")

    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="pv-section-hdr">Frequently Asked Questions</div>', unsafe_allow_html=True)

    faqs = [
        ("How is the Health Score calculated?",
         "The AI analyzes your recent updates, milestones, decisions, and blockers to generate a 0–100 score. Active projects with regular updates and resolved blockers score higher."),
        ("How do I share a project with someone?",
         "Open the project → Settings tab → Share section. Copy the read-only link and send it. They can view but not edit."),
        ("Can I import from GitHub / Notion / Google Docs?",
         "Yes — click Import in the sidebar. You can paste text, upload a file, or connect Google Drive. AI will extract project context automatically."),
        ("How do I invite a collaborator to edit a project?",
         "Open the project → Settings tab → Collaborators section. Enter their email and assign a role (editor or viewer)."),
        ("Will my data be deleted if I archive a project?",
         "No. Archived projects are hidden from the dashboard but all data, updates, and snapshots are preserved. You can restore anytime."),
        ("What AI models power ProjectVault?",
         "ProjectVault uses Groq (Llama / Mixtral) by default. You can also configure an OpenAI key in Settings for GPT-4 access."),
    ]

    for q, a in faqs:
        st.markdown(
            f'<div class="help-faq"><div class="help-faq-q">{_html.escape(q)}</div><div class="help-faq-a">{_html.escape(a)}</div></div>',
            unsafe_allow_html=True,
        )

with col_info:
    st.markdown('<div class="pv-section-hdr">Quick Help</div>', unsafe_allow_html=True)
    categories = [
        ("Bug Report", "Something is broken or not working as expected."),
        ("Feature Request", "Suggest a new feature or improvement."),
        ("Data & Imports", "Questions about importing projects or AI analysis."),
        ("Account", "Login issues, billing, or profile settings."),
    ]
    for title, desc in categories:
        st.markdown(
            f'<div class="help-cat-card">'
            f'<div class="help-cat-title">{title}</div>'
            f'<div class="help-cat-desc">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="pv-section-hdr">Response Time</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);border-radius:14px;padding:1rem 1.25rem;font-size:0.82rem;color:#6B4A3E;line-height:1.7;">'
        '<strong style="color:#2C1810;">When to expect a reply</strong><br>'
        'All requests are reviewed by the ProjectVault team. Expect a response within 1–2 business days.'
        '</div>',
        unsafe_allow_html=True,
    )
