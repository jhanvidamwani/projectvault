import re


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def is_valid_github_url(url: str) -> bool:
    return url.startswith("https://github.com/") and len(url.split("/")) >= 5


def sanitize_tags(raw: str) -> list[str]:
    return [t.strip().lower() for t in raw.split(",") if t.strip()]
