from __future__ import annotations
from services.auth_service import get_supabase, get_supabase_admin

PLATFORM_PRESETS: dict[str, dict] = {
    "claude":      {"icon": "", "label": "Claude",       "domain": "claude.ai"},
    "chatgpt":     {"icon": "", "label": "ChatGPT",      "domain": "chat.openai.com"},
    "notion":      {"icon": "", "label": "Notion",       "domain": "notion.so"},
    "figma":       {"icon": "", "label": "Figma",        "domain": "figma.com"},
    "jira":        {"icon": "", "label": "Jira",         "domain": "atlassian.net"},
    "slack":       {"icon": "", "label": "Slack",        "domain": "slack.com"},
    "googledocs":  {"icon": "", "label": "Google Docs",  "domain": "docs.google.com"},
    "loom":        {"icon": "", "label": "Loom",         "domain": "loom.com"},
    "linear":      {"icon": "", "label": "Linear",       "domain": "linear.app"},
    "github":      {"icon": "", "label": "GitHub",       "domain": "github.com"},
    "other":       {"icon": "", "label": "Link",         "domain": ""},
}

_DOMAIN_MAP = {
    "notion.so":          "notion",
    "claude.ai":          "claude",
    "chat.openai.com":    "chatgpt",
    "figma.com":          "figma",
    "atlassian.net":      "jira",
    "slack.com":          "slack",
    "docs.google.com":    "googledocs",
    "loom.com":           "loom",
    "linear.app":         "linear",
    "github.com":         "github",
}


def detect_platform(url: str) -> dict:
    url_lower = url.lower()
    for domain, platform in _DOMAIN_MAP.items():
        if domain in url_lower:
            return {"platform": platform, **PLATFORM_PRESETS[platform]}
    return {"platform": "other", **PLATFORM_PRESETS["other"]}


def get_project_links(project_id: str) -> list[dict]:
    admin = get_supabase_admin()
    resp = (
        admin.table("project_links")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def add_project_link(
    project_id: str,
    user_id: str,
    platform: str,
    label: str,
    url: str,
    icon: str,
) -> dict:
    admin = get_supabase_admin()
    resp = admin.table("project_links").insert({
        "project_id": project_id,
        "user_id": user_id,
        "platform": platform,
        "label": label,
        "url": url,
        "icon": icon,
    }).execute()
    return resp.data[0] if resp.data else {}


def delete_project_link(link_id: str, user_id: str) -> bool:
    admin = get_supabase_admin()
    admin.table("project_links").delete().eq("id", link_id).execute()
    return True
