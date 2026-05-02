from datetime import datetime, timezone

_PLACEHOLDER_DESCS = frozenset({
    "project imported from provided content.",
    "no description provided.",
})


def format_date(iso_str: str, include_time: bool = False) -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if include_time:
            return dt.strftime("%b %d, %Y %H:%M")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso_str[:10]


def relative_time(iso_str: str) -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = seconds // 60
            return f"{m}m ago"
        if seconds < 86400:
            h = seconds // 3600
            return f"{h}h ago"
        d = seconds // 86400
        if d == 1:
            return "yesterday"
        if d < 30:
            return f"{d}d ago"
        return format_date(iso_str)
    except Exception:
        return iso_str[:10]


def truncate(text: str, max_len: int = 120) -> str:
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len].rstrip() + "..."


def clean_description(desc: str | None) -> str:
    """Return description, or empty string if it's a known placeholder."""
    if not desc:
        return ""
    stripped = desc.strip()
    if stripped.lower() in _PLACEHOLDER_DESCS:
        return ""
    return stripped


def health_color_class(score: int) -> str:
    if score >= 70:
        return "health-green"
    if score >= 40:
        return "health-yellow"
    return "health-red"


def health_icon(score: int) -> str:
    return ""
