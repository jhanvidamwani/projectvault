from __future__ import annotations
import html as _html
import re
import streamlit as st
from utils.formatting import format_date

_clean = lambda t: re.sub(r'<[^>]+>', '', str(t or '')).strip()

SOURCE_LABELS = {
    "update":          "Update",
    "snapshot":        "Snapshot",
    "github_commit":   "GitHub",
    "ai_conversation": "AI Chat",
}

TYPE_CHIP = {
    "update":          ("#8E5E4E", "#FFE4D8"),
    "snapshot":        ("#8E5E4E", "#FFE4D8"),
    "github_commit":   ("#8E5E4E", "#FFE4D8"),
    "ai_conversation": ("#C4A882", "rgba(196,168,130,0.15)"),
}


def render_search_results(results: list[dict]):
    if not results:
        st.markdown(
            '<div style="padding:3rem 0;text-align:center;color:#A88F87;font-size:0.875rem;line-height:1.6;">'
            'No results found. Try a different query or broaden your filters.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div style="color:#A88F87;font-size:0.72rem;margin-bottom:0.5rem;">'
        f'{len(results)} result{"s" if len(results) != 1 else ""}</div>',
        unsafe_allow_html=True,
    )

    rows_html = ""
    for r in results:
        source_type    = r.get("source_type", "update")
        label          = SOURCE_LABELS.get(source_type, source_type.replace("_", " ").title())
        chip_clr, chip_bg = TYPE_CHIP.get(source_type, ("#999999", "rgba(255,255,255,0.04)"))
        similarity     = r.get("similarity", 0)
        project_title  = _html.escape(_clean(r.get("project_title", "Unknown")))
        meta           = r.get("metadata") or {}
        date_str       = _html.escape(format_date(meta.get("created_at") or r.get("created_at", "")))
        content        = _html.escape(_clean(r.get("content", "")))[:300]
        raw_url        = meta.get("url") or ""
        sim_pct        = int(similarity * 100)
        sim_clr        = "#8E5E4E" if sim_pct >= 80 else ("#C4A882" if sim_pct >= 60 else "#A88F87")

        gh_link = ""
        if raw_url and raw_url.startswith(("http://", "https://")):
            url_safe = _html.escape(raw_url)
            gh_link = (
                f'<div style="margin-top:0.4rem;">'
                f'<a href="{url_safe}" target="_blank" rel="noopener noreferrer" '
                f'style="color:#E07060;font-size:0.78rem;text-decoration:none;">View on GitHub</a>'
                f'</div>'
            )

        rows_html += f"""
        <div class="pv-sr-row">
            <div class="pv-sr-body">
                <div class="pv-sr-project">{project_title}</div>
                <div class="pv-sr-content">{content}</div>
                {gh_link}
            </div>
            <div class="pv-sr-meta">
                <span class="pv-sr-chip" style="color:{chip_clr};background:{chip_bg};">{label.upper()}</span>
                <span class="pv-sr-sim" style="color:{sim_clr};">{sim_pct}%</span>
                <span class="pv-sr-date">{date_str}</span>
            </div>
        </div>
        """

    st.markdown(rows_html, unsafe_allow_html=True)
