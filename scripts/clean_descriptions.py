#!/usr/bin/env python3
"""One-time script: strip HTML/JSON from project description fields in Supabase."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.auth_service import get_supabase_admin


def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', str(text))
    clean = ' '.join(clean.split()).strip()
    if "imported from provided" in clean.lower():
        return ""
    if len(clean) < 3:
        return ""
    return clean


def main():
    admin = get_supabase_admin()
    projects = admin.table("projects").select("id, title, description").execute().data
    print(f"Found {len(projects)} projects to check.")

    updated = 0
    for p in projects:
        raw = p.get("description") or ""
        cleaned = strip_html(raw)
        if cleaned != raw:
            final = cleaned if cleaned else None
            admin.table("projects").update({"description": final}).eq("id", p["id"]).execute()
            title = (p.get("title") or "")[:40]
            print(f"  Cleaned [{title}]: {repr(raw[:60])} → {repr((final or '')[:60])}")
            updated += 1

    print(f"\nDone. {updated} of {len(projects)} project descriptions cleaned.")


if __name__ == "__main__":
    main()
