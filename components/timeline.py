from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
from utils.formatting import format_date


def render_timeline(snapshots: list[dict], on_select_key: str = "selected_snapshot"):
    """Render an interactive Plotly snapshot timeline."""
    if not snapshots:
        st.markdown('<div class="empty-state"><h3>No snapshots yet</h3><p>Create your first snapshot to start tracking project history.</p></div>', unsafe_allow_html=True)
        return

    dates = [s["created_at"][:10] for s in snapshots]
    titles = [s.get("title", "Snapshot") for s in snapshots]
    triggers = [s.get("trigger", "manual") for s in snapshots]
    ids = [s["id"] for s in snapshots]

    trigger_colors = {
        "manual": "#253245",
        "auto": "#8ab5a0",
        "milestone": "#c4a882",
        "integration": "#8ab5a0",
    }
    colors = [trigger_colors.get(t, "#253245") for t in triggers]

    hover_texts = []
    for s in snapshots:
        narrative = s.get("ai_narrative") or "No narrative."
        hover_texts.append(
            f"<b>{s.get('title', 'Snapshot')}</b><br>"
            f"{s['created_at'][:10]}<br>"
            f"Trigger: {s.get('trigger', 'manual')}<br><br>"
            f"{narrative[:200]}..."
        )

    fig = go.Figure()

    # Timeline line
    fig.add_trace(go.Scatter(
        x=dates,
        y=[0] * len(dates),
        mode="lines",
        line=dict(color="#c8ddd5", width=3),
        hoverinfo="skip",
    ))

    # Snapshot dots
    fig.add_trace(go.Scatter(
        x=dates,
        y=[0] * len(dates),
        mode="markers+text",
        marker=dict(size=18, color=colors, line=dict(width=2, color="#f4f6f4")),
        text=[str(i + 1) for i in range(len(snapshots))],
        textposition="middle center",
        textfont=dict(color="#f4f6f4", size=10),
        hovertext=hover_texts,
        hoverinfo="text",
        customdata=ids,
    ))

    fig.update_layout(
        paper_bgcolor="#f4f6f4",
        plot_bgcolor="#f4f6f4",
        font=dict(color="#253245"),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11),
        ),
        yaxis=dict(visible=False, range=[-0.5, 0.5]),
        margin=dict(l=20, r=20, t=20, b=40),
        height=140,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Snapshot selector
    st.markdown("**Select a snapshot to view:**")
    cols = st.columns(min(len(snapshots), 4))
    for i, snap in enumerate(snapshots):
        with cols[i % 4]:
            label = f"#{i+1} {snap['created_at'][:10]}"
            if st.button(label, key=f"snap_select_{snap['id']}", use_container_width=True):
                st.session_state[on_select_key] = snap["id"]

    # Show selected snapshot detail
    selected_id = st.session_state.get(on_select_key)
    if selected_id:
        selected = next((s for s in snapshots if s["id"] == selected_id), None)
        if selected:
            st.divider()
            st.markdown(f"### {selected.get('title', 'Snapshot')}")
            st.markdown(f"**Created:** {format_date(selected['created_at'], include_time=True)} · **Trigger:** {selected.get('trigger', 'manual')}")
            if selected.get("ai_narrative"):
                st.info(f"**AI Narrative:** {selected['ai_narrative']}")
            return selected
    return None
