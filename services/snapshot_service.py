from __future__ import annotations
from datetime import datetime, timezone
from services import db_service as db
from services import ai_service as ai


def create_snapshot(project_id: str, user_id: str, title: str = "", trigger: str = "manual") -> dict:
    current_state = db.get_project_full_state(project_id)
    previous = db.get_latest_snapshot(project_id)

    if not title:
        title = f"Snapshot — {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M')}"

    narrative = ""
    if previous:
        narrative = ai.generate_snapshot_narrative(
            before=previous.get("snapshot_data", {}),
            after=current_state,
        )

    snapshot = {
        "project_id": project_id,
        "created_by": user_id,
        "title": title,
        "snapshot_data": current_state,
        "ai_narrative": narrative,
        "trigger": trigger,
    }
    return db.insert_snapshot(snapshot)


def rollback_to_snapshot(snapshot_id: str, user_id: str, project_id: str) -> bool:
    """Restore project state from a snapshot (updates + metadata)."""
    snapshot = db.get_snapshot(snapshot_id)
    if not snapshot or snapshot["project_id"] != project_id:
        return False

    saved_state = snapshot.get("snapshot_data", {})
    project_data = saved_state.get("project", {})

    if project_data:
        db.update_project(project_id, {
            "title": project_data.get("title"),
            "description": project_data.get("description"),
            "status": project_data.get("status"),
            "tags": project_data.get("tags"),
        })

    # Record rollback as an update
    db.add_update(
        project_id=project_id,
        user_id=user_id,
        content=f"Project rolled back to snapshot: '{snapshot['title']}' ({snapshot['created_at'][:10]})",
        update_type="decision",
        ai_summary="Project state restored from a previous snapshot.",
    )

    # Auto-snapshot after rollback
    create_snapshot(project_id, user_id, title=f"Post-rollback snapshot", trigger="auto")
    return True


def compare_snapshots(snapshot_id_a: str, snapshot_id_b: str) -> dict:
    snap_a = db.get_snapshot(snapshot_id_a)
    snap_b = db.get_snapshot(snapshot_id_b)
    if not snap_a or not snap_b:
        return {"error": "One or both snapshots not found."}

    ai_comparison = ai.compare_snapshots_ai(snap_a, snap_b)

    # Structural diff
    data_a = snap_a.get("snapshot_data", {})
    data_b = snap_b.get("snapshot_data", {})

    updates_a = {u["id"] for u in data_a.get("updates", [])}
    updates_b = {u["id"] for u in data_b.get("updates", [])}

    return {
        "snapshot_a": snap_a,
        "snapshot_b": snap_b,
        "ai_comparison": ai_comparison,
        "updates_added": len(updates_b - updates_a),
        "updates_removed": len(updates_a - updates_b),
        "project_a": data_a.get("project", {}),
        "project_b": data_b.get("project", {}),
    }
