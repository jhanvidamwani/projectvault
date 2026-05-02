import re
import html as _html
import streamlit as st
from utils.formatting import health_icon, health_color_class, relative_time, clean_description

_clean = lambda t: re.sub(r'<[^>]+>', '', _html.unescape(str(t or ''))).strip()


def render_project_card(project: dict, on_open_key: str):
    health = project.get("health_score") or 0
    status = project.get("status", "active")
    status_color_map = {
        "active": "#8ab5a0",
        "paused": "#c4a882",
        "completed": "#253245",
        "archived": "#7a8f8a",
    }
    color = status_color_map.get(status, "#999999")
    tags = project.get("tags") or []
    tags_html = " ".join(f'<span class="tag tag-note">{_html.escape(_clean(t))}</span>' for t in tags[:4])
    updated = relative_time(project.get("updated_at", ""))

    title_safe = _html.escape(_clean(project.get("title") or "Untitled"))
    desc = clean_description(_clean(project.get("description") or ""))
    desc_safe = _html.escape(desc[:140] + "…" if len(desc) > 140 else desc)

    col_card, col_btn = st.columns([8, 1])
    with col_card:
        st.markdown(f"""
        <div class="pv-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:1.05rem; font-weight:700;">{title_safe}</span>
                <span class="{health_color_class(health)}">{health}/100</span>
            </div>
            <div style="font-size:0.75rem; color:{color}; margin-top:2px;">● {status.capitalize()} · {updated}</div>
            {f'<div style="color:#999999; font-size:0.88rem; margin-top:0.35rem;">{desc_safe}</div>' if desc_safe else ''}
            <div style="margin-top:0.5rem;">{tags_html}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.write("")
        st.write("")
        return st.button("Open", key=on_open_key, use_container_width=True)
