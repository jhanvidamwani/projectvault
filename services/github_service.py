from __future__ import annotations
import os
import streamlit as st
from datetime import datetime, timezone


def _get_token() -> str:
    return st.session_state.get("github_token") or os.getenv("GITHUB_TOKEN", "")


def _parse_repo_path(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    url = url.rstrip("/")
    if "github.com/" in url:
        return url.split("github.com/")[-1]
    return url


def sync_repo(repo_url: str, project_id: str) -> dict:
    """Sync commits, PRs, and issues from a GitHub repo into the project."""
    from github import Github, GithubException
    from services import db_service as db
    from services import ai_service as ai

    token = _get_token()
    if not token:
        return {"error": "No GitHub token configured. Add it in Settings."}

    repo_path = _parse_repo_path(repo_url)
    try:
        g = Github(token)
        repo = g.get_repo(repo_path)
    except GithubException as e:
        return {"error": f"GitHub error: {e.data.get('message', str(e))}"}

    synced = {"commits": 0, "pull_requests": 0, "issues": 0, "errors": []}

    # ── Commits ──────────────────────────────────────────────
    try:
        for commit in repo.get_commits()[:50]:  # last 50
            content = (
                f"Commit: {commit.commit.message[:200]}"
                f" | Author: {commit.commit.author.name}"
                f" | Date: {commit.commit.author.date.isoformat()}"
                f" | SHA: {commit.sha[:8]}"
            )
            embedding = ai.generate_embedding(content)
            if embedding:
                _upsert_embedding(project_id, "github_commit", commit.sha, content, embedding, {
                    "sha": commit.sha,
                    "author": commit.commit.author.name,
                    "url": commit.html_url,
                    "date": commit.commit.author.date.isoformat(),
                })
            synced["commits"] += 1
    except Exception as e:
        synced["errors"].append(f"Commits: {e}")

    # ── Pull Requests ─────────────────────────────────────────
    try:
        for pr in repo.get_pulls(state="all")[:30]:
            content = (
                f"PR #{pr.number}: {pr.title}"
                f" | State: {pr.state}"
                f" | Author: {pr.user.login}"
                f" | {pr.body[:300] if pr.body else ''}"
            )
            embedding = ai.generate_embedding(content)
            if embedding:
                _upsert_embedding(project_id, "github_commit", f"pr-{pr.number}", content, embedding, {
                    "type": "pull_request",
                    "number": pr.number,
                    "state": pr.state,
                    "url": pr.html_url,
                })
            synced["pull_requests"] += 1
    except Exception as e:
        synced["errors"].append(f"PRs: {e}")

    # ── Issues ────────────────────────────────────────────────
    try:
        for issue in repo.get_issues(state="all")[:30]:
            if issue.pull_request:
                continue  # skip PR-issues
            content = (
                f"Issue #{issue.number}: {issue.title}"
                f" | State: {issue.state}"
                f" | Author: {issue.user.login}"
                f" | {issue.body[:300] if issue.body else ''}"
            )
            embedding = ai.generate_embedding(content)
            if embedding:
                _upsert_embedding(project_id, "github_commit", f"issue-{issue.number}", content, embedding, {
                    "type": "issue",
                    "number": issue.number,
                    "state": issue.state,
                    "url": issue.html_url,
                })
            synced["issues"] += 1
    except Exception as e:
        synced["errors"].append(f"Issues: {e}")

    # Update integration last_synced_at
    _update_integration_sync(project_id)

    return synced


def get_recent_commits(repo_url: str, limit: int = 10) -> list[dict]:
    from github import Github, GithubException
    token = _get_token()
    if not token:
        return []
    try:
        g = Github(token)
        repo = g.get_repo(_parse_repo_path(repo_url))
        result = []
        for commit in repo.get_commits()[:limit]:
            result.append({
                "sha": commit.sha[:8],
                "message": commit.commit.message.split("\n")[0][:120],
                "author": commit.commit.author.name,
                "date": commit.commit.author.date.isoformat()[:10],
                "url": commit.html_url,
            })
        return result
    except Exception:
        return []


def _upsert_embedding(project_id: str, source_type: str, source_id: str, content: str, embedding: list, metadata: dict):
    from services.auth_service import get_supabase
    supabase = get_supabase()
    supabase.table("embeddings").upsert({
        "project_id": project_id,
        "source_type": source_type,
        "source_id": source_id,
        "content": content,
        "embedding": embedding,
        "metadata": metadata,
    }, on_conflict="source_id,project_id").execute()


def _update_integration_sync(project_id: str):
    from services.auth_service import get_supabase
    supabase = get_supabase()
    supabase.table("integrations").update({
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }).eq("project_id", project_id).eq("integration_type", "github").execute()
