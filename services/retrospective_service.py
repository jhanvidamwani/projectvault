from __future__ import annotations
from services import db_service as db
from services import ai_service as ai


def generate_and_store(project_id: str, user_id: str, trigger: str = "manual") -> dict:
    """Generate an AI retrospective and persist it."""
    project_data = db.get_project_full_state(project_id)
    project_data["snapshots"] = db.get_snapshots(project_id)

    retro_content = ai.generate_retrospective(project_data)

    # If generation failed, raise so the UI can show a clean error
    summary = retro_content.get("executive_summary", "")
    if summary.startswith("Retrospective generation failed"):
        raise RuntimeError(summary.replace("Retrospective generation failed: ", ""))

    retro = db.insert_retrospective({
        "project_id": project_id,
        "generated_by": user_id,
        "trigger": trigger,
        "content": retro_content,
        "ai_model_used": ai._active_model(),
    })
    return retro


def get_latest(project_id: str) -> dict | None:
    retros = db.get_retrospectives(project_id)
    return retros[0] if retros else None
