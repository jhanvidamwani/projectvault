import os
import html as _html
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="ProjectVault — Search",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth
from utils.sidebar import render_sidebar
from services import db_service as db, search_service
from services.ai_service import _openai_key
from components.search_results import render_search_results

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""<style>
/* ── Search bar ──────────────────────────────────── */
div[data-testid="stTextInput"] input {
    background:    #FFFFFF !important;
    border:        1.5px solid rgba(142,94,78,0.22) !important;
    border-radius: 12px !important;
    color:         #2C1810 !important;
    height:        48px !important;
    font-size:     0.875rem !important;
    padding:       0 14px !important;
}
div[data-testid="stTextInput"] input::placeholder { color: #A88F87 !important; }
div[data-testid="stTextInput"] input:focus {
    border-color: #E88D7D !important;
    box-shadow:   0 0 0 3px rgba(232,141,125,0.12) !important;
    outline:      none !important;
}
/* Search button height matches input */
div[data-testid="stColumns"] div.stButton > button[kind="primary"] {
    height: 48px !important;
    border-radius: 12px !important;
}
/* ── Example chips ───────────────────────────────── */
.pv-search-chip-row div.stButton > button {
    background:    #FFFFFF !important;
    border:        1px solid rgba(142,94,78,0.22) !important;
    border-radius: 999px !important;
    color:         #6B4A3E !important;
    font-size:     0.78rem !important;
    font-weight:   500 !important;
    transition:    background 150ms ease, border-color 150ms ease !important;
}
.pv-search-chip-row div.stButton > button:hover {
    background:   rgba(232,141,125,0.1) !important;
    border-color: rgba(224,112,96,0.4) !important;
    color:        #2C1810 !important;
}
/* ── Search result rows ──────────────────────────── */
.pv-sr-row {
    display:       flex;
    align-items:   flex-start;
    gap:           1rem;
    padding:       0.9rem 0;
    border-bottom: 1px solid rgba(142,94,78,0.1);
}
.pv-sr-row:last-child { border-bottom: none; }
.pv-sr-body        { flex: 1; min-width: 0; }
.pv-sr-project {
    font-size:      0.65rem;
    font-weight:    700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color:          #E07060;
    margin-bottom:  0.3rem;
}
.pv-sr-content {
    font-size:   0.875rem;
    color:       #2C1810;
    line-height: 1.55;
}
.pv-sr-meta {
    display:        flex;
    flex-direction: column;
    align-items:    flex-end;
    gap:            0.35rem;
    flex-shrink:    0;
    padding-top:    0.1rem;
}
.pv-sr-chip {
    font-size:      0.58rem;
    font-weight:    700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding:        2px 8px;
    border-radius:  999px;
    white-space:    nowrap;
}
.pv-sr-date { font-size: 0.72rem; color: #A88F87; white-space: nowrap; }
.pv-sr-sim  { font-size: 0.72rem; font-weight: 600; white-space: nowrap; }
.pv-try-label {
    font-size:      0.625rem;
    font-weight:    700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color:          #A88F87;
    margin-bottom:  0.6rem;
}
/* ── Filters section ─────────────────────────────── */
.pv-filter-hdr {
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #A88F87; margin-bottom: 0.5rem;
}
</style>""", unsafe_allow_html=True)

require_auth()
user = st.session_state.user
all_projects = db.get_projects_for_user(user["id"])
render_sidebar(user, active="search", projects=all_projects)

if "pv_search_q" not in st.session_state:
    st.session_state["pv_search_q"] = ""

# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="margin-bottom:1.75rem;">'
    '<h2 style="margin:0 0 0.3rem;font-size:1.75rem;font-weight:700;color:#2C1810;line-height:1.2;">Semantic Search</h2>'
    '<p style="color:#7A6560;font-size:0.8125rem;margin:0;">Search across all your projects, notes, decisions, and snapshots.</p>'
    '</div>',
    unsafe_allow_html=True,
)

has_openai = bool(_openai_key() and not _openai_key().startswith("your_"))
if not has_openai:
    st.info("Running in text search mode. Add an OpenAI key in Settings to enable vector semantic search.")

if not all_projects:
    st.markdown('<div style="padding:3rem 0;text-align:center;color:#A88F87;font-size:0.875rem;">No projects yet — create one first to enable search.</div>', unsafe_allow_html=True)
    st.stop()

project_map = {p["id"]: p["title"] for p in all_projects}

if "pv_search_prefill" in st.session_state:
    st.session_state["pv_search_q"] = st.session_state.pop("pv_search_prefill")

# ── Search bar ──────────────────────────────────────────────────────────────────
col_query, col_search = st.columns([5, 1])
with col_query:
    query = st.text_input(
        "Search query",
        placeholder='e.g. "why did we pivot to GraphQL", "performance bottleneck", "auth decisions"',
        label_visibility="collapsed",
        key="pv_search_q",
    )
with col_search:
    do_search = st.button("Search", type="primary", use_container_width=True, key="pv_search_btn")

if st.session_state.pop("pv_do_search", False):
    do_search = True

# ── Filters (always visible, no expander) ──────────────────────────────────────
st.markdown('<div class="pv-filter-hdr">Filters</div>', unsafe_allow_html=True)
col_proj, col_type, col_thresh = st.columns(3)
with col_proj:
    selected_projects = st.multiselect(
        "Scope to projects",
        list(project_map.keys()),
        default=list(project_map.keys()),
        format_func=lambda x: project_map[x],
        label_visibility="collapsed",
    )
with col_type:
    source_types = st.multiselect(
        "Source types",
        ["update", "snapshot", "github_commit", "ai_conversation"],
        default=["update", "snapshot", "github_commit", "ai_conversation"],
        format_func=lambda x: {
            "update": "Project Updates",
            "snapshot": "Snapshots",
            "github_commit": "GitHub",
            "ai_conversation": "AI Conversations",
        }[x],
        label_visibility="collapsed",
    )
with col_thresh:
    threshold = st.slider(
        "Similarity threshold", 0.3, 0.95, 0.65, 0.05,
        help="Higher = stricter matching (only for vector search)",
        disabled=not has_openai,
    )

st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

# ── Example chips ───────────────────────────────────────────────────────────────
if not query:
    st.markdown('<div class="pv-try-label">Try asking</div>', unsafe_allow_html=True)
    examples = [
        "Authentication decisions",
        "Performance issues",
        "Scope creep",
        "Security vulnerabilities",
        "Architecture debates",
    ]
    st.markdown('<div class="pv-search-chip-row">', unsafe_allow_html=True)
    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        with cols[i]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state["pv_search_prefill"] = ex
                st.session_state["pv_do_search"] = True
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Results ─────────────────────────────────────────────────────────────────────
if do_search and query.strip():
    if not selected_projects:
        st.error("Select at least one project to search.")
    else:
        with st.spinner(f"Searching across {len(selected_projects)} project(s)..."):
            results = search_service.semantic_search(
                query=query.strip(),
                project_ids=selected_projects,
                source_types=source_types if source_types else None,
                match_threshold=threshold,
                match_count=30,
            )
        st.markdown(
            '<div style="background:#FFFFFF;border:1px solid rgba(142,94,78,0.18);border-radius:16px;padding:0.75rem 1.25rem;margin-top:0.5rem;box-shadow:0 2px 8px rgba(142,94,78,0.07);">',
            unsafe_allow_html=True,
        )
        render_search_results(results)
        st.markdown('</div>', unsafe_allow_html=True)
elif do_search and not query.strip():
    st.error("Enter a search query.")
