#!/usr/bin/env python3
"""
Clean ALL HTML and junk from every text field in projects, updates, and snapshots.
Run once: python3 scripts/clean_all_text.py
"""
import os, re, sys, html as _html
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from services.auth_service import get_supabase_admin

JUNK_PHRASES = {
    "project imported from provided content.",
    "project imported from provided content",
    "content was imported. ai analysis unavailable",
    "no content available",
}


def clean(text: str, max_chars: int = 0) -> str:
    if not text:
        return ""
    # Unescape HTML entities first (&lt; → <, etc.)
    t = _html.unescape(str(text))
    # Strip all HTML tags
    t = re.sub(r'<[^>]+>', '', t)
    # Collapse whitespace
    t = ' '.join(t.split()).strip()
    # Drop known junk phrases
    if t.lower() in JUNK_PHRASES:
        return ""
    if any(t.lower().startswith(j) for j in JUNK_PHRASES):
        return ""
    # Truncate if requested
    if max_chars and len(t) > max_chars:
        t = t[:max_chars].rstrip() + "…"
    return t


def main():
    admin = get_supabase_admin()
    total_cleaned = 0

    # ── Projects ────────────────────────────────────────────────────────────────
    print("Cleaning projects table…")
    projects = admin.table("projects").select("id, title, description, health_explanation").execute().data
    for p in projects:
        updates = {}
        cleaned_desc = clean(p.get("description") or "")
        if cleaned_desc != (p.get("description") or ""):
            updates["description"] = cleaned_desc or None

        cleaned_exp = clean(p.get("health_explanation") or "")
        if cleaned_exp != (p.get("health_explanation") or ""):
            updates["health_explanation"] = cleaned_exp or None

        if updates:
            admin.table("projects").update(updates).eq("id", p["id"]).execute()
            print(f"  Project [{(p.get('title') or '')[:30]}]: {list(updates.keys())}")
            total_cleaned += 1

    # ── Updates ─────────────────────────────────────────────────────────────────
    print("\nCleaning updates table…")
    updates_rows = admin.table("updates").select("id, content, ai_summary, update_type").execute().data
    for u in updates_rows:
        row_updates = {}

        raw_content = u.get("content") or ""
        cleaned_content = clean(raw_content, max_chars=1000)
        if cleaned_content != raw_content:
            row_updates["content"] = cleaned_content

        raw_summ = u.get("ai_summary") or ""
        cleaned_summ = clean(raw_summ, max_chars=300)
        if cleaned_summ != raw_summ:
            row_updates["ai_summary"] = cleaned_summ

        if row_updates:
            admin.table("updates").update(row_updates).eq("id", u["id"]).execute()
            preview = (cleaned_content or "")[:50]
            print(f"  Update [{u['update_type']}] '{preview}…': {list(row_updates.keys())}")
            total_cleaned += 1

    # ── Snapshots ───────────────────────────────────────────────────────────────
    print("\nCleaning snapshots table…")
    snapshots = admin.table("snapshots").select("id, title, ai_narrative").execute().data
    for s in snapshots:
        row_updates = {}

        for field in ("ai_narrative",):
            raw = s.get(field) or ""
            cleaned = clean(raw, max_chars=500)
            if cleaned != raw:
                row_updates[field] = cleaned or None

        if row_updates:
            admin.table("snapshots").update(row_updates).eq("id", s["id"]).execute()
            print(f"  Snapshot [{(s.get('title') or '')[:30]}]: {list(row_updates.keys())}")
            total_cleaned += 1

    print(f"\nDone. {total_cleaned} rows updated across all tables.")


if __name__ == "__main__":
    main()
