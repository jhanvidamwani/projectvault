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


# ── GitHub repo file import ───────────────────────────────────────────────────
def fetch_repo_zip(repo_url: str, branch: str = "") -> dict:
    """Download a GitHub repo as ZIP and return its bytes + metadata.

    Returns: {"bytes": <zip>, "repo_path": "owner/repo", "branch": "main", "error": None}
             or {"error": "...", "bytes": None}
    """
    import requests
    repo_path = _parse_repo_path(repo_url)
    if "/" not in repo_path:
        return {"error": "URL must be in form github.com/owner/repo", "bytes": None}

    token = _get_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Get default branch if none specified
    if not branch:
        try:
            r = requests.get(
                f"https://api.github.com/repos/{repo_path}",
                headers=headers, timeout=15,
            )
            if r.status_code == 404:
                return {"error": "Repository not found (or private without a token).", "bytes": None}
            if r.status_code == 401:
                return {"error": "Invalid GitHub token. Update it in Settings.", "bytes": None}
            if r.status_code != 200:
                return {"error": f"GitHub API error: {r.status_code}", "bytes": None}
            branch = r.json().get("default_branch", "main")
        except Exception as e:
            return {"error": f"Network error: {e}", "bytes": None}

    # Download zipball
    try:
        zip_url = f"https://api.github.com/repos/{repo_path}/zipball/{branch}"
        zr = requests.get(zip_url, headers=headers, timeout=60, stream=True)
        if zr.status_code != 200:
            return {"error": f"Could not download repo ({zr.status_code})", "bytes": None}
        # Stream-collect; cap at 50 MB so we don't OOM the free tier
        max_bytes = 50 * 1024 * 1024
        chunks, total = [], 0
        for chunk in zr.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                return {"error": "Repository is larger than 50 MB — too big for free tier.", "bytes": None}
        return {
            "bytes": b"".join(chunks),
            "repo_path": repo_path,
            "branch": branch,
            "error": None,
        }
    except Exception as e:
        return {"error": f"Download failed: {e}", "bytes": None}


def get_recent_commits(repo_url: str, limit: int = 10) -> list:
    """Fetch recent commits — used by project page sync."""
    from github import Github, GithubException
    token = _get_token()
    if not token:
        return []
    try:
        g = Github(token)
        repo = g.get_repo(_parse_repo_path(repo_url))
        return [{"sha": c.sha[:8], "message": c.commit.message[:120], "url": c.html_url}
                for c in repo.get_commits()[:limit]]
    except GithubException:
        return []


# ── GitHub live file browser (Option B: fetch on-demand) ──────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_file_tree(repo_url: str, branch: str = "") -> dict:
    """Return full file tree for a repo. Cached 5 min.

    Returns: {"tree": [{"path","type","size","sha"}], "branch": "main", "error": None}
    """
    import requests
    repo_path = _parse_repo_path(repo_url)
    if "/" not in repo_path:
        return {"error": "Invalid repo URL", "tree": []}

    token = _get_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        if not branch:
            r = requests.get(f"https://api.github.com/repos/{repo_path}", headers=headers, timeout=10)
            if r.status_code != 200:
                return {"error": f"Repo not found ({r.status_code})", "tree": []}
            branch = r.json().get("default_branch", "main")

        r = requests.get(
            f"https://api.github.com/repos/{repo_path}/git/trees/{branch}?recursive=1",
            headers=headers, timeout=15,
        )
        if r.status_code != 200:
            return {"error": f"Could not fetch tree ({r.status_code})", "tree": []}

        data = r.json()
        tree = [
            {"path": e["path"], "type": e["type"], "size": e.get("size", 0), "sha": e["sha"]}
            for e in data.get("tree", [])
        ]
        return {"tree": tree, "branch": branch, "truncated": data.get("truncated", False), "error": None}
    except Exception as e:
        return {"error": str(e), "tree": []}


@st.cache_data(ttl=300, show_spinner=False)
def get_file_content(repo_url: str, path: str, branch: str = "main") -> dict:
    """Fetch single file content. Cached 5 min per (repo, path, branch).

    Returns: {"content": "...", "size": 1234, "encoding": "utf-8", "error": None, "binary": False}
    """
    import requests, base64
    repo_path = _parse_repo_path(repo_url)
    token = _get_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo_path}/contents/{path}",
            params={"ref": branch}, headers=headers, timeout=15,
        )
        if r.status_code != 200:
            return {"content": "", "error": f"Could not fetch ({r.status_code})", "size": 0, "binary": False}
        data = r.json()
        size = data.get("size", 0)

        # Skip very large files
        if size > 1_000_000:
            return {"content": "", "error": "File too large to preview (>1 MB)", "size": size, "binary": False}

        raw = base64.b64decode(data.get("content", ""))
        # Detect binary
        try:
            content = raw.decode("utf-8")
            return {"content": content, "size": size, "encoding": "utf-8", "binary": False, "error": None}
        except UnicodeDecodeError:
            return {"content": "", "size": size, "binary": True, "error": None}
    except Exception as e:
        return {"content": "", "error": str(e), "size": 0, "binary": False}
