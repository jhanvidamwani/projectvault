from __future__ import annotations
import streamlit as st
from utils.formatting import format_date


def render_snapshot_compare(snapshots: list[dict], project_id: str, user_id: str):
    if len(snapshots) < 2:
        st.info("You need at least 2 snapshots to compare.")
        return

    options = {s["id"]: f"{s.get('title', 'Snapshot')} ({s['created_at'][:10]})" for s in snapshots}
    ids = list(options.keys())

    col_a, col_b = st.columns(2)
    with col_a:
        id_a = st.selectbox("Snapshot A", ids, format_func=lambda x: options[x], key="compare_a")
    with col_b:
        id_b = st.selectbox("Snapshot B", ids, index=min(1, len(ids)-1), format_func=lambda x: options[x], key="compare_b")

    if st.button("Compare Snapshots", type="primary"):
        if id_a == id_b:
            st.error("Select two different snapshots.")
            return

        with st.spinner("AI is comparing snapshots..."):
            from services.snapshot_service import compare_snapshots
            result = compare_snapshots(id_a, id_b)

        if "error" in result:
            st.error(result["error"])
            return

        snap_a = result["snapshot_a"]
        snap_b = result["snapshot_b"]

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**A — {snap_a.get('title', 'Snapshot')}**")
            st.caption(format_date(snap_a["created_at"], include_time=True))
            proj_a = result.get("project_a", {})
            st.markdown(f"Status: `{proj_a.get('status', 'unknown')}`")
        with col2:
            st.markdown(f"**B — {snap_b.get('title', 'Snapshot')}**")
            st.caption(format_date(snap_b["created_at"], include_time=True))
            proj_b = result.get("project_b", {})
            st.markdown(f"Status: `{proj_b.get('status', 'unknown')}`")

        col1.metric("Updates", len(result.get("snapshot_a", {}).get("snapshot_data", {}).get("updates", [])))
        col2.metric("Updates", len(result.get("snapshot_b", {}).get("snapshot_data", {}).get("updates", [])), delta=result.get("updates_added", 0))

        st.divider()
        st.markdown("### AI Analysis")
        st.markdown(result.get("ai_comparison", "No comparison available."))
