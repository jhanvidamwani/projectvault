import os
import io
import json
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

st.set_page_config(
    page_title="ProjectVault — AI Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth
from utils.sidebar import render_sidebar
from services import ai_service as ai, search_service, db_service as db

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""<style>
/* ── Chat bubbles ─────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border:     none !important;
    padding:    0.4rem 0 !important;
    gap:        0.5rem !important;
}
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
    display: none !important;
}
/* User bubble — navy, right aligned */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    flex-direction:  row-reverse !important;
    justify-content: flex-start !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) > div:last-child {
    background:    #2C1810 !important;
    border-radius: 6px !important;
    max-width:     70% !important;
    padding:       10px 14px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .stMarkdown,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .stMarkdown p {
    color: #ffffff !important;
}
/* AI bubble — white card, left aligned */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) > div:last-child {
    background:    #FFFFFF !important;
    border:        1px solid rgba(142,94,78,0.12) !important;
    border-radius: 6px !important;
    max-width:     82% !important;
    padding:       12px 16px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) .stMarkdown,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) .stMarkdown p {
    color: #2C1810 !important;
}
/* ── Suggestion chips — white cards ───────────── */
div.stButton > button[kind="secondary"] {
    background:      #ffffff !important;
    border:          1px solid rgba(142,94,78,0.12) !important;
    border-radius:   8px !important;
    color:           #6B4A3E !important;
    text-align:      left !important;
    justify-content: flex-start !important;
    padding:         0.75rem 1rem !important;
    height:          auto !important;
    min-height:      3rem !important;
    font-size:       0.875rem !important;
    line-height:     1.4 !important;
    transition:      border-color 150ms ease, color 150ms ease !important;
}
div.stButton > button[kind="secondary"]:hover {
    border-color: #2C1810 !important;
    color:        #2C1810 !important;
    background:   #FFFFFF !important;
}
/* ── Chat input — white ───────────────────────── */
[data-testid="stChatInput"] {
    background:    #FFFFFF !important;
    border:        1px solid rgba(142,94,78,0.2) !important;
    border-radius: 12px !important;
    box-shadow:    none !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #E88D7D !important;
    box-shadow:   0 0 0 3px rgba(232,141,125,0.1) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color:      #2C1810 !important;
    font-size:  0.875rem !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #A88F87 !important;
}
[data-testid="stChatInput"] button {
    background:    #E88D7D !important;
    border-radius: 8px !important;
    border:        none !important;
}
[data-testid="stChatInput"] button:hover {
    background: #CF6F61 !important;
}
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user


# ── Portfolio PDF generator ───────────────────────────────────────────────────

def _ensure_reportlab():
    try:
        from reportlab.lib.pagesizes import letter
    except ImportError:
        import subprocess, sys as _sys
        subprocess.check_call([_sys.executable, "-m", "pip", "install", "reportlab", "-q"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def generate_portfolio_pdf(user_name: str, projects: list[dict]) -> bytes:
    _ensure_reportlab()
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak, HRFlowable)
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from datetime import date

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title=f"{user_name} — Project Portfolio",
    )

    # ── Colour palette ────────────────────────────────────────────────────────
    DARK   = colors.HexColor("#1e1e1e")
    PURPLE = colors.HexColor("#2C1810")
    CYAN   = colors.HexColor("#E88D7D")
    SLATE  = colors.HexColor("#2c2c2c")
    LIGHT  = colors.HexColor("#f0f0f0")
    MUTED  = colors.HexColor("#666666")
    GREEN  = colors.HexColor("#E88D7D")
    YELLOW = colors.HexColor("#C4A882")
    RED    = colors.HexColor("#CF6F61")

    STATUS_COLOR = {
        "active": GREEN, "completed": CYAN,
        "paused": YELLOW, "archived": MUTED,
    }

    def health_color(score):
        if score >= 70: return GREEN
        if score >= 40: return YELLOW
        return RED

    # ── Styles ────────────────────────────────────────────────────────────────
    cover_title  = ParagraphStyle("CT", fontSize=38, textColor=LIGHT,
                                  fontName="Helvetica-Bold", alignment=TA_CENTER,
                                  spaceAfter=8, leading=44)
    cover_sub    = ParagraphStyle("CS", fontSize=14, textColor=MUTED,
                                  fontName="Helvetica", alignment=TA_CENTER,
                                  spaceAfter=4)
    cover_date   = ParagraphStyle("CD", fontSize=11, textColor=SLATE,
                                  fontName="Helvetica", alignment=TA_CENTER)
    proj_name    = ParagraphStyle("PN", fontSize=20, textColor=DARK,
                                  fontName="Helvetica-Bold", spaceAfter=4, leading=24)
    section_hdr  = ParagraphStyle("SH", fontSize=9, textColor=PURPLE,
                                  fontName="Helvetica-Bold", spaceBefore=10,
                                  spaceAfter=3, textTransform="uppercase",
                                  letterSpacing=0.8)
    body_text    = ParagraphStyle("BT", fontSize=10, textColor=SLATE,
                                  fontName="Helvetica", spaceAfter=3,
                                  leading=15)
    bullet_text  = ParagraphStyle("BU", fontSize=9.5, textColor=SLATE,
                                  fontName="Helvetica", spaceAfter=2,
                                  leftIndent=12, leading=14)
    tag_style    = ParagraphStyle("TG", fontSize=8.5, textColor=PURPLE,
                                  fontName="Helvetica-Bold")

    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 2.2 * inch))
    story.append(Paragraph("Project Portfolio", cover_title))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(user_name, cover_sub))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(date.today().strftime("%B %d, %Y"), cover_date))
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE, spaceAfter=0.25 * inch))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"{len(projects)} project{'s' if len(projects) != 1 else ''} · Generated by ProjectVault",
                            cover_date))
    story.append(PageBreak())

    # ── One page per project ──────────────────────────────────────────────────
    for idx, project in enumerate(projects):
        title   = project.get("title", "Untitled")
        desc    = project.get("description") or "No description provided."
        status  = project.get("status", "active")
        health  = project.get("health_score") or 0
        tags    = project.get("tags") or []
        created = (project.get("created_at") or "")[:10]
        h_expl  = project.get("health_explanation") or ""

        # Fetch updates from DB
        try:
            updates = db.get_updates(project["id"], limit=20)
        except Exception:
            updates = []

        milestones = [u for u in updates if u.get("update_type") == "milestone"]
        decisions  = [u for u in updates if u.get("update_type") == "decision"]
        blockers   = [u for u in updates if u.get("update_type") == "blocker"]
        recent     = updates[:6]

        # Header band (dark background table)
        _shex = "22c55e" if status == "active" else "06b6d4" if status == "completed" else "eab308" if status == "paused" else "94a3b8"
        hdr_data = [[Paragraph(f"<font color='#f0f0f0'><b>{title}</b></font>", proj_name),
                     Paragraph(f"<font color='#{_shex}'><b>{status.upper()}</b></font>",
                               ParagraphStyle("S", fontSize=10, fontName="Helvetica-Bold",
                                              alignment=1, textColor=STATUS_COLOR.get(status, MUTED)))]]
        hdr_tbl = Table(hdr_data, colWidths=[5.5 * inch, 1.5 * inch])
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DARK),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (0, 0), 14),
            ("RIGHTPADDING", (1, 0), (1, 0), 14),
            ("TOPPADDING",   (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 14),
            ("ROUNDEDCORNERS", (0, 0), (-1, -1), [6, 6, 6, 6]),
        ]))
        story.append(hdr_tbl)
        story.append(Spacer(1, 0.18 * inch))

        # Meta row: health + created
        h_color = health_color(health)
        meta_data = [[
            Paragraph(f"Health Score", section_hdr),
            Paragraph(f"Created", section_hdr),
            Paragraph(f"Category", section_hdr),
        ], [
            Paragraph(f"<font color='{h_color.hexval()}'><b>{health}/100</b></font>",
                      ParagraphStyle("HS", fontSize=16, fontName="Helvetica-Bold",
                                     textColor=h_color)),
            Paragraph(created or "—", body_text),
            Paragraph(", ".join(tags) if tags else "—", tag_style),
        ]]
        meta_tbl = Table(meta_data, colWidths=[2.37 * inch, 2.37 * inch, 2.37 * inch])
        meta_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f0f0")),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#f0f0f0")),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ]))
        story.append(meta_tbl)
        story.append(Spacer(1, 0.18 * inch))

        # Description
        story.append(Paragraph("Description", section_hdr))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#f0f0f0"), spaceAfter=4))
        story.append(Paragraph(desc[:500], body_text))
        if h_expl:
            story.append(Paragraph(f"AI assessment: {h_expl}", bullet_text))
        story.append(Spacer(1, 0.1 * inch))

        # Milestones
        if milestones:
            story.append(Paragraph("Key Milestones", section_hdr))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#f0f0f0"), spaceAfter=4))
            for m in milestones[:5]:
                dt = (m.get("created_at") or "")[:10]
                content = (m.get("content") or "")[:140]
                story.append(Paragraph(f"{content}  <font color='#999999'>({dt})</font>", bullet_text))
            story.append(Spacer(1, 0.1 * inch))

        # Key decisions
        if decisions:
            story.append(Paragraph("Key Decisions", section_hdr))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#f0f0f0"), spaceAfter=4))
            for d in decisions[:4]:
                story.append(Paragraph(f"{(d.get('content') or '')[:140]}", bullet_text))
            story.append(Spacer(1, 0.1 * inch))

        # Blockers
        if blockers:
            story.append(Paragraph("Blockers", section_hdr))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#f0f0f0"), spaceAfter=4))
            for b in blockers[:3]:
                story.append(Paragraph(f"{(b.get('content') or '')[:140]}", bullet_text))
            story.append(Spacer(1, 0.1 * inch))

        # Recent activity
        if recent:
            story.append(Paragraph("Recent Activity", section_hdr))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#f0f0f0"), spaceAfter=4))
            for u in recent:
                utype = (u.get("update_type") or "note").upper()
                dt = (u.get("created_at") or "")[:10]
                content = (u.get("content") or "")[:120]
                story.append(Paragraph(
                    f"<font color='#2C1810'>[{utype}]</font>  {content}  "
                    f"<font color='#999999'>({dt})</font>", bullet_text))

        if idx < len(projects) - 1:
            story.append(PageBreak())

    # ── Page numbers ──────────────────────────────────────────────────────────
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(letter[0] / 2, 0.4 * inch,
                                 f"Page {doc.page}  ·  ProjectVault Portfolio")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return buf.getvalue()


# ── Sidebar ───────────────────────────────────────────────────────────────────
import html as _html_mod
_all_proj = db.get_projects_for_user(user["id"])
render_sidebar(user, active="ai", projects=_all_proj)

# ── Header ────────────────────────────────────────────────────────────────────
_hcol_title, _hcol_clear, _hcol_pdf = st.columns([4, 1, 1.4])
with _hcol_title:
    st.markdown("""
<div style="margin-bottom:1.75rem;">
    <h2 style="margin:0 0 0.3rem;font-size:1.75rem;font-weight:700;color:#2C1810;line-height:1.2;">AI Assistant</h2>
    <p style="color:#A88F87;font-size:0.8125rem;margin:0;line-height:1.5;">
        Ask anything about your project history.
    </p>
</div>
""", unsafe_allow_html=True)
with _hcol_clear:
    st.write("")
    st.write("")
    if st.button("Clear Chat", use_container_width=True, key="clear_chat_hdr"):
        st.session_state["portfolio_chat_history"] = []
        st.rerun()
with _hcol_pdf:
    st.write("")
    st.write("")
    if st.button("Export Portfolio", type="primary", use_container_width=True, help="Download all projects as a PDF"):
        try:
            _all_projects = db.get_projects_for_user(user["id"])
            if not _all_projects:
                st.warning("No projects to export yet.")
            else:
                with st.spinner("Generating PDF..."):
                    _pdf_bytes = generate_portfolio_pdf(user.get("name", ""), _all_projects)
                st.session_state["_portfolio_pdf"] = _pdf_bytes
                st.rerun()
        except Exception as _e:
            st.error(f"PDF generation failed: {str(_e)[:120]}")
    if st.session_state.get("_portfolio_pdf"):
        st.download_button(
            label="Save PDF",
            data=st.session_state["_portfolio_pdf"],
            file_name=f"portfolio_{user.get('name','').replace(' ','_').lower()}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
            key="pdf_dl_main",
        )

# ── Check AI available ────────────────────────────────────────────────────────
groq_ok = bool(ai._groq_key() and not ai._groq_key().startswith("your_"))

if not groq_ok:
    st.markdown("""
    <div class="pv-card" style="padding:1.25rem;">
        <div style="font-weight:600; color:#6B4A3E; margin-bottom:0.4rem;">AI key not configured</div>
        <div style="color:#A88F87; font-size:0.87rem; line-height:1.6;">
            Get a free Groq key at <strong>console.groq.com/keys</strong> and add it as
            <code>GROQ_API_KEY</code> in your <code>.env</code> file, then restart.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Load user projects ─────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def _get_user_projects(user_id: str) -> list[dict]:
    return db.get_projects_for_user(user_id)

projects = _get_user_projects(user["id"])
project_ids = [p["id"] for p in projects]

if not project_ids:
    st.markdown("<small style='color:#666'>No projects yet. Create a project first to enable AI Assistant.</small>", unsafe_allow_html=True)
    st.stop()

# ── Chat history ──────────────────────────────────────────────────────────────
if "portfolio_chat_history" not in st.session_state:
    st.session_state["portfolio_chat_history"] = []

history: list[dict] = st.session_state["portfolio_chat_history"]

# ── Example prompts ───────────────────────────────────────────────────────────
if not history:
    st.markdown(
        '<div style="font-size:0.625rem;color:#A88F87;text-transform:uppercase;'
        'letter-spacing:0.1em;font-weight:700;margin-bottom:0.75rem;">Try asking</div>',
        unsafe_allow_html=True,
    )
    examples = [
        "Which of my projects has the most technical debt?",
        "Summarize everything I built in the last 3 months",
        "What decisions did I make about authentication?",
        "Which projects have active blockers right now?",
    ]
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        if cols[i % 2].button(ex, use_container_width=True, key=f"ex_{i}"):
            st.session_state["portfolio_prefill"] = ex
            st.rerun()
    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ── Render history ────────────────────────────────────────────────────────────
for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"Sources ({len(msg['sources'])})", expanded=False):
                for src in msg["sources"]:
                    st.markdown(
                        f"**{src.get('project_title', 'Unknown')}** · `{src.get('source_type', '')}` "
                        f"· similarity {src.get('similarity', 0):.2f}\n\n"
                        f"> {src.get('content', '')[:200]}…"
                    )

# ── Input ─────────────────────────────────────────────────────────────────────
prefill = st.session_state.pop("portfolio_prefill", "")
query = st.chat_input("Ask anything about your projects…") or prefill

if query:
    with st.chat_message("user"):
        st.markdown(query)
    history.append({"role": "user", "content": query})

    with st.spinner("Searching across your projects…"):
        chunks = search_service.semantic_search(
            query, project_ids, match_threshold=0.55, match_count=10,
        )

    if not chunks:
        project_summaries = []
        for p in projects[:5]:
            updates = db.get_updates(p["id"], limit=10)
            update_texts = " | ".join(u.get("content", "")[:100] for u in updates[:5])
            project_summaries.append(
                f"Project: {p['title']} (status: {p.get('status','active')}, health: {p.get('health_score',0)})\n"
                f"Recent updates: {update_texts or 'none'}"
            )
        context_text = "\n\n".join(project_summaries)
        fallback = True
    else:
        context_parts = []
        for c in chunks[:10]:
            context_parts.append(
                f"[{c.get('source_type','').upper()} · Project: {c.get('project_title','Unknown')}]\n"
                f"{c.get('content','')}"
            )
        context_text = "\n\n---\n\n".join(context_parts)[:6000]
        fallback = False

    system_prompt = (
        "You are ProjectVault's portfolio AI assistant. Answer the user's question using ONLY "
        "the context below, which contains excerpts from their project history. "
        "Be specific — name which project each insight comes from. "
        "If the context doesn't contain enough information, say so clearly.\n\n"
        f"RELEVANT PROJECT CONTEXT:\n{context_text}"
    )

    history_parts = []
    for m in history[-8:]:
        role = "User" if m["role"] == "user" else "Assistant"
        history_parts.append(f"{role}: {m['content']}")

    user_prompt = ("\n\n".join(history_parts[:-1]) + f"\n\nUser: {query}") if len(history_parts) > 1 else query

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                response_text = ai._generate(system_prompt, user_prompt, max_tokens=1200)
            except Exception as e:
                response_text = f"Couldn't generate a response right now. {str(e)[:80]}"
        st.markdown(response_text)
        if chunks:
            with st.expander(f"Sources ({len(chunks)})", expanded=False):
                for src in chunks:
                    st.markdown(
                        f"**{src.get('project_title', 'Unknown')}** · `{src.get('source_type', '')}` "
                        f"· similarity {src.get('similarity', 0):.2f}\n\n"
                        f"> {src.get('content', '')[:200]}…"
                    )

    history.append({"role": "assistant", "content": response_text, "sources": chunks})
    st.session_state["portfolio_chat_history"] = history
