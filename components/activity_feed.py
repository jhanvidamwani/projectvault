import html as _html
import re
import streamlit as st
from utils.formatting import relative_time

_clean = lambda t: re.sub(r'<[^>]+>', '', str(t or '')).strip()

TYPE_META = {
    "note":      ("tag-note",      "NOTE"),
    "decision":  ("tag-decision",  "DECISION"),
    "milestone": ("tag-milestone", "MILESTONE"),
    "blocker":   ("tag-blocker",   "BLOCKER"),
    "pivot":     ("tag-pivot",     "PIVOT"),
}


def render_update_card(update: dict, show_delete: bool = False, delete_key: str = "") -> bool:
    utype = update.get("update_type", "note")
    css_cls, label = TYPE_META.get(utype, ("tag-note", "NOTE"))
    time_str  = relative_time(update.get("created_at", ""))
    summary   = _html.escape(_clean(update.get("ai_summary") or ""))
    content   = _html.escape(_clean(update.get("content", "")))

    col_card, col_del = st.columns([9, 1]) if show_delete else (st.container(), None)

    with col_card:
        st.markdown(f"""
        <div class="pv-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <span class="tag {css_cls}">{label}</span>
                <span style="color:#666666; font-size:0.75rem;">{time_str}</span>
            </div>
            <div style="margin-top:0.5rem; font-size:0.875rem; color:#f0f0f0; line-height:1.5;">{content}</div>
            {f'<div style="margin-top:0.4rem; color:#666666; font-size:0.78rem; font-style:italic;">{summary}</div>' if summary else ''}
        </div>
        """, unsafe_allow_html=True)

    if show_delete and col_del:
        with col_del:
            st.write("")
            st.write("")
            return st.button("×", key=delete_key, help="Delete update")
    return False


def render_activity_feed(updates: list[dict], can_edit: bool = False, on_delete=None):
    if not updates:
        st.markdown('<div class="empty-state"><h3>No updates yet</h3></div>', unsafe_allow_html=True)
        return

    for u in updates:
        deleted = render_update_card(
            u,
            show_delete=can_edit,
            delete_key=f"del_feed_{u['id']}",
        )
        if deleted and on_delete:
            on_delete(u["id"])
