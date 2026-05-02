from __future__ import annotations
from services import ai_service as ai
from services.auth_service import get_supabase, get_supabase_admin
from services import db_service as db


def embed_update(update: dict, project_id: str) -> bool:
    """Embed a project update and store in the vector table."""
    content = f"[{update.get('update_type', 'note').upper()}] {update['content']}"
    embedding = ai.generate_embedding(content)
    if not embedding:
        return False
    admin = get_supabase_admin()
    admin.table("embeddings").upsert({
        "project_id": project_id,
        "source_type": "update",
        "source_id": str(update["id"]),
        "content": content,
        "embedding": embedding,
        "metadata": {
            "update_type": update.get("update_type"),
            "created_at": update.get("created_at"),
        },
    }, on_conflict="source_id,project_id").execute()
    return True


def embed_snapshot(snapshot: dict, project_id: str) -> bool:
    """Embed a snapshot narrative."""
    narrative = snapshot.get("ai_narrative") or snapshot.get("title", "")
    if not narrative:
        return False
    embedding = ai.generate_embedding(narrative)
    if not embedding:
        return False
    admin = get_supabase_admin()
    admin.table("embeddings").upsert({
        "project_id": project_id,
        "source_type": "snapshot",
        "source_id": str(snapshot["id"]),
        "content": narrative,
        "embedding": embedding,
        "metadata": {
            "title": snapshot.get("title"),
            "created_at": snapshot.get("created_at"),
            "trigger": snapshot.get("trigger"),
        },
    }, on_conflict="source_id,project_id").execute()
    return True


def semantic_search(
    query: str,
    project_ids: list[str],
    source_types: list[str] | None = None,
    match_threshold: float = 0.65,
    match_count: int = 20,
) -> list[dict]:
    """Search across content — uses vector similarity if available, falls back to keyword search."""
    results = []

    # Try vector search if embedding can be generated
    query_embedding = ai.generate_embedding(query)
    if query_embedding:
        try:
            admin = get_supabase_admin()
            resp = admin.rpc("search_embeddings", {
                "query_embedding": query_embedding,
                "p_project_ids": project_ids,
                "match_threshold": match_threshold,
                "match_count": match_count,
            }).execute()
            results = resp.data or []
        except Exception:
            pass

    # Fall back to keyword search if no vector results
    if not results:
        results = _fallback_search(query, project_ids, match_count)

    if source_types:
        results = [r for r in results if r.get("source_type") in source_types]

    # Enrich with project name
    project_map: dict[str, str | None] = {pid: None for pid in project_ids}
    for r in results:
        pid = r.get("project_id")
        if pid and project_map.get(pid) is None:
            project = db.get_project(pid)
            project_map[pid] = project.get("title", "Unknown") if project else "Unknown"
        r["project_title"] = project_map.get(pid, "Unknown")

    return results


def _fallback_search(query: str, project_ids: list[str], limit: int) -> list[dict]:
    """Keyword search: tries embeddings table first, then falls back to updates table directly."""
    admin = get_supabase_admin()
    q = query.strip().lower()
    results: list[dict] = []

    # 1. Search embeddings table (populated if OpenAI key was ever used)
    try:
        resp = (
            admin.table("embeddings")
            .select("id, content, source_type, source_id, project_id, metadata")
            .in_("project_id", project_ids)
            .ilike("content", f"%{q}%")
            .limit(limit)
            .execute()
        )
        for r in (resp.data or []):
            r["similarity"] = 0.5
        results = resp.data or []
    except Exception:
        pass

    if results:
        return results

    # 2. Search updates table directly (always populated)
    try:
        resp = (
            admin.table("updates")
            .select("id, content, update_type, project_id, created_at, ai_summary")
            .in_("project_id", project_ids)
            .ilike("content", f"%{q}%")
            .limit(limit)
            .execute()
        )
        for r in (resp.data or []):
            r["similarity"] = 0.45
            r["source_type"] = "update"
            r["source_id"]   = str(r.get("id", ""))
            r["metadata"]    = {
                "created_at":  r.get("created_at"),
                "update_type": r.get("update_type"),
            }
        results.extend(resp.data or [])
    except Exception:
        pass

    # 3. Also search ai_summary field
    try:
        resp = (
            admin.table("updates")
            .select("id, content, update_type, project_id, created_at, ai_summary")
            .in_("project_id", project_ids)
            .ilike("ai_summary", f"%{q}%")
            .limit(limit)
            .execute()
        )
        seen = {r["source_id"] for r in results}
        for r in (resp.data or []):
            if str(r.get("id", "")) in seen:
                continue
            r["similarity"]  = 0.4
            r["source_type"] = "update"
            r["source_id"]   = str(r.get("id", ""))
            r["content"]     = r.get("ai_summary") or r.get("content", "")
            r["metadata"]    = {
                "created_at":  r.get("created_at"),
                "update_type": r.get("update_type"),
            }
            results.append(r)
    except Exception:
        pass

    # 4. Search snapshots table
    try:
        resp = (
            admin.table("snapshots")
            .select("id, ai_narrative, title, project_id, created_at, trigger")
            .in_("project_id", project_ids)
            .ilike("ai_narrative", f"%{q}%")
            .limit(limit)
            .execute()
        )
        for r in (resp.data or []):
            r["similarity"]  = 0.4
            r["source_type"] = "snapshot"
            r["source_id"]   = str(r.get("id", ""))
            r["content"]     = r.get("ai_narrative") or r.get("title", "")
            r["metadata"]    = {
                "created_at": r.get("created_at"),
                "title":      r.get("title"),
                "trigger":    r.get("trigger"),
            }
            results.append(r)
    except Exception:
        pass

    return results[:limit]


def reindex_project(project_id: str) -> dict:
    """Re-embed all updates and snapshots for a project."""
    updates = db.get_updates(project_id, limit=500)
    snapshots = db.get_snapshots(project_id)

    embedded_updates   = sum(1 for u in updates   if embed_update(u, project_id))
    embedded_snapshots = sum(1 for s in snapshots if embed_snapshot(s, project_id))

    return {
        "updates_indexed":   embedded_updates,
        "snapshots_indexed": embedded_snapshots,
        "total":             embedded_updates + embedded_snapshots,
    }
