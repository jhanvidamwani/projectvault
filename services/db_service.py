from __future__ import annotations
import streamlit as st
from services.auth_service import get_supabase, get_supabase_admin
from typing import Optional


# ============================================================
# PROJECTS
# ============================================================

def create_project(owner_id: str, title: str, description: str = "", tags: list[str] = None) -> dict:
    """Note: invalidates cache on success."""
    admin = get_supabase_admin()
    data = {
        "owner_id": owner_id,
        "title": title,
        "description": description,
        "status": "active",
        "tags": tags or [],
        "health_score": 80,
    }
    response = admin.table("projects").insert(data).execute()
    project = response.data[0]
    # Auto-add owner as collaborator
    admin.table("collaborators").insert({
        "project_id": project["id"],
        "user_id": owner_id,
        "role": "owner",
        "invited_by": owner_id,
    }).execute()
    _invalidate_project_caches()
    return project


@st.cache_data(ttl=30, show_spinner=False)
def get_projects_for_user(user_id: str) -> list[dict]:
    admin = get_supabase_admin()
    owned = admin.table("projects").select("*").eq("owner_id", user_id).execute().data

    collab_rows = admin.table("collaborators").select("project_id").eq("user_id", user_id).neq("role", "owner").execute().data
    collab_ids = [r["project_id"] for r in collab_rows]

    collab_projects = []
    if collab_ids:
        collab_projects = admin.table("projects").select("*").in_("id", collab_ids).execute().data

    all_projects = owned + collab_projects
    all_projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return all_projects


@st.cache_data(ttl=30, show_spinner=False)
def get_project(project_id: str) -> Optional[dict]:
    admin = get_supabase_admin()
    response = admin.table("projects").select("*").eq("id", project_id).limit(1).execute()
    return response.data[0] if response.data else None


def update_project(project_id: str, updates: dict) -> dict:
    admin = get_supabase_admin()
    from datetime import datetime, timezone
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    response = admin.table("projects").update(updates).eq("id", project_id).execute()
    _invalidate_project_caches()
    return response.data[0]


def delete_project(project_id: str) -> None:
    admin = get_supabase_admin()
    admin.table("projects").delete().eq("id", project_id).execute()
    _invalidate_project_caches()


def _invalidate_project_caches() -> None:
    """Clear cached project/update queries so fresh data is fetched on next read."""
    try:
        get_projects_for_user.clear()
        get_project.clear()
        get_recent_updates_for_user.clear()
        get_milestones_for_user.clear()
    except Exception:
        pass


def get_project_by_share_token(share_token: str) -> Optional[dict]:
    admin = get_supabase_admin()
    response = admin.table("projects").select("*").eq("share_token", share_token).execute()
    return response.data[0] if response.data else None


# ============================================================
# UPDATES / ACTIVITY LOG
# ============================================================

def add_update(project_id: str, user_id: str, content: str, update_type: str = "note", metadata: dict = None, ai_summary: str = "") -> dict:
    admin = get_supabase_admin()
    data = {
        "project_id": project_id,
        "user_id": user_id,
        "content": content,
        "update_type": update_type,
        "ai_summary": ai_summary,
        "metadata": metadata or {},
    }
    response = admin.table("updates").insert(data).execute()
    from datetime import datetime, timezone
    admin.table("projects").update({"updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", project_id).execute()
    return response.data[0]


def get_updates(project_id: str, limit: int = 50) -> list[dict]:
    admin = get_supabase_admin()
    response = (
        admin.table("updates")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


@st.cache_data(ttl=30, show_spinner=False)
def get_recent_updates_for_user(project_ids: list[str], limit: int = 10) -> list[dict]:
    if not project_ids:
        return []
    admin = get_supabase_admin()
    response = (
        admin.table("updates")
        .select("*")
        .in_("project_id", project_ids)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


@st.cache_data(ttl=30, show_spinner=False)
def get_milestones_for_user(project_ids: list[str], limit: int = 8) -> list[dict]:
    if not project_ids:
        return []
    admin = get_supabase_admin()
    response = (
        admin.table("updates")
        .select("*")
        .in_("project_id", project_ids)
        .eq("update_type", "milestone")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def delete_update(update_id: str) -> None:
    admin = get_supabase_admin()
    admin.table("updates").delete().eq("id", update_id).execute()


# ============================================================
# SNAPSHOTS
# ============================================================

def insert_snapshot(snapshot: dict) -> dict:
    admin = get_supabase_admin()
    response = admin.table("snapshots").insert(snapshot).execute()
    return response.data[0]


def get_snapshots(project_id: str) -> list[dict]:
    admin = get_supabase_admin()
    response = (
        admin.table("snapshots")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def get_latest_snapshot(project_id: str) -> Optional[dict]:
    admin = get_supabase_admin()
    response = (
        admin.table("snapshots")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_snapshot(snapshot_id: str) -> Optional[dict]:
    admin = get_supabase_admin()
    response = admin.table("snapshots").select("*").eq("id", snapshot_id).limit(1).execute()
    return response.data[0] if response.data else None


def get_project_full_state(project_id: str) -> dict:
    project = get_project(project_id)
    updates = get_updates(project_id, limit=100)
    return {
        "project": project,
        "updates": updates,
        "integrations": {},
        "collaborators": get_collaborators(project_id),
        "metadata": {
            "snapshot_version": "1.0",
        }
    }


# ============================================================
# COLLABORATORS
# ============================================================

def get_collaborators(project_id: str) -> list[dict]:
    admin = get_supabase_admin()
    collabs = admin.table("collaborators").select("*").eq("project_id", project_id).execute().data
    if not collabs:
        return []
    user_ids = [c["user_id"] for c in collabs if c.get("user_id")]
    if user_ids:
        users_data = admin.table("users").select("id, name, email, avatar_url").in_("id", user_ids).execute().data
        by_id = {u["id"]: u for u in users_data}
        for c in collabs:
            c["users"] = by_id.get(c.get("user_id"), {})
    return collabs


def add_collaborator(project_id: str, user_id: str, role: str, invited_by: str) -> dict:
    admin = get_supabase_admin()
    data = {
        "project_id": project_id,
        "user_id": user_id,
        "role": role,
        "invited_by": invited_by,
    }
    response = admin.table("collaborators").insert(data).execute()
    return response.data[0]


def get_user_role(project_id: str, user_id: str) -> Optional[str]:
    admin = get_supabase_admin()
    response = (
        admin.table("collaborators")
        .select("role")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    return response.data[0]["role"] if response.data else None


def get_user_by_email(email: str) -> Optional[dict]:
    admin = get_supabase_admin()
    response = admin.table("users").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None


# ============================================================
# RETROSPECTIVES
# ============================================================

def insert_retrospective(retro: dict) -> dict:
    admin = get_supabase_admin()
    response = admin.table("retrospectives").insert(retro).execute()
    return response.data[0]


def get_retrospectives(project_id: str) -> list[dict]:
    admin = get_supabase_admin()
    response = (
        admin.table("retrospectives")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data
