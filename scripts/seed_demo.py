"""
Seed script — populates 3 realistic demo projects with 6 months of history.
Run from the projectvault/ directory:
    python scripts/seed_demo.py

Requires a .env file with SUPABASE_URL, SUPABASE_KEY, and a valid user account.
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.auth_service import get_supabase
from services import db_service as db, ai_service as ai, snapshot_service

DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@projectvault.app")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo1234")
DEMO_NAME = "Demo User"

PROJECTS = [
    {
        "title": "Auth Infrastructure Rewrite",
        "description": "Replacing legacy session-based auth with JWT + OAuth2. Required by security audit Q1 2024.",
        "status": "completed",
        "tags": ["backend", "security", "auth", "infrastructure"],
        "github_repo_url": "https://github.com/demo/auth-rewrite",
        "updates": [
            ("decision", "Decided to use Supabase Auth over rolling our own — saves 3 weeks of dev time.", -180),
            ("note", "Security audit flagged our cookie-based sessions as non-compliant with SOC2 requirements.", -175),
            ("milestone", "Completed threat model review with security team. 12 attack vectors identified and mitigated.", -160),
            ("blocker", "Supabase Auth doesn't support SAML out of the box. Need to evaluate workarounds.", -145),
            ("decision", "Decided against SAML for v1. Will add as an enterprise feature in Q3. Unblocked.", -140),
            ("pivot", "Switched from Passport.js to Supabase client library after discovering better RLS support.", -120),
            ("milestone", "JWT auth live in staging. All API endpoints protected. Zero regression in tests.", -100),
            ("note", "Performance testing shows 18% improvement in auth latency over old session approach.", -85),
            ("blocker", "Google OAuth callback URL misconfigured in production. Down for 2 hours. Fixed.", -70),
            ("milestone", "Full rollout to production. Migrated 47k user sessions. No data loss.", -50),
            ("decision", "Decided to keep old auth endpoints alive for 30 days for gradual client migration.", -40),
            ("milestone", "Old auth endpoints deprecated. Migration complete. Project closed.", -5),
        ],
    },
    {
        "title": "Dashboard Performance Initiative",
        "description": "Main dashboard P95 load time is 8.2s. Target: under 2s. Driven by Q2 OKR.",
        "status": "active",
        "tags": ["frontend", "performance", "react", "optimization"],
        "github_repo_url": "https://github.com/demo/dashboard-perf",
        "updates": [
            ("note", "Baseline established: P95 = 8.2s, P50 = 4.1s. 73% of time is in API waterfall.", -90),
            ("decision", "Decided to prioritize API parallelization over frontend caching — higher ROI.", -85),
            ("blocker", "Data team's API doesn't support batch requests. Workaround needed.", -80),
            ("pivot", "Switched strategy: build BFF (Backend for Frontend) layer to batch upstream calls.", -72),
            ("milestone", "BFF prototype deployed to staging. P95 dropped to 4.8s. 41% improvement.", -60),
            ("decision", "Approved switching to React Query for client-side caching. Eliminates redundant fetches.", -55),
            ("note", "Identified 3 N+1 query patterns in project list endpoint. Root cause of 40% of load time.", -48),
            ("milestone", "N+1 queries fixed. P95 now 3.1s in staging.", -35),
            ("blocker", "React Query migration broke team filters in Safari. Investigating.", -28),
            ("decision", "Safari bug traced to sessionStorage polyfill. Fixed in react-query v5.22. Upgraded.", -20),
            ("milestone", "Full React Query rollout. P95 = 2.4s. Close to target.", -10),
            ("note", "Final optimization pass: virtualized project list. P95 = 1.9s. OKR met.", -2),
        ],
    },
    {
        "title": "AI Feature: Smart Project Summaries",
        "description": "Build an AI-powered weekly digest for PMs. Automatically summarizes project activity and surfaces risks.",
        "status": "active",
        "tags": ["ai", "ml", "product", "claude"],
        "github_repo_url": "https://github.com/demo/ai-summaries",
        "updates": [
            ("note", "PM research: 8/10 PMs say they miss important updates because they don't have time to read everything.", -60),
            ("decision", "Chose Claude (claude-sonnet-4-6) as primary AI engine. Best at structured summarization.", -55),
            ("milestone", "POC: Feeding 30 days of project updates to Claude, getting 5-bullet weekly digest. Quality is high.", -48),
            ("blocker", "Context window limits mean we can't send all updates at once for large projects. Need chunking strategy.", -40),
            ("decision", "Decided to use semantic clustering to select most important updates per time window. Reduces tokens by 60%.", -32),
            ("note", "A/B test shows PMs using AI digest spend 40% less time in weekly standups.", -24),
            ("pivot", "Added proactive risk detection — AI flags projects with blockers open > 7 days. Not in original spec but high value.", -18),
            ("milestone", "Beta launched to 15 PMs. NPS score: 72. Key feedback: 'Finally, something that actually helps.'", -10),
            ("decision", "Expanding to all PM users next sprint. No quota limits for now — monitoring costs.", -3),
        ],
    },
]


def seed():
    supabase = get_supabase()

    # Create or fetch demo user
    try:
        resp = supabase.auth.sign_in_with_password({"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        user_id = str(resp.user.id)
        print(f"Signed in as {DEMO_EMAIL}")
    except Exception:
        resp = supabase.auth.sign_up({"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "options": {"data": {"name": DEMO_NAME}}})
        if not resp.user:
            print("ERROR: Could not create demo user. Update DEMO_EMAIL/DEMO_PASSWORD in .env")
            sys.exit(1)
        user_id = str(resp.user.id)
        supabase.table("users").upsert({"id": user_id, "email": DEMO_EMAIL, "name": DEMO_NAME}).execute()
        print(f"Created demo user: {DEMO_EMAIL}")

    now = datetime.now(timezone.utc)

    for proj_data in PROJECTS:
        updates_spec = proj_data.pop("updates")

        # Create project
        project = db.create_project(
            owner_id=user_id,
            title=proj_data["title"],
            description=proj_data["description"],
            tags=proj_data["tags"],
        )
        project_id = project["id"]

        # Set status and GitHub URL
        db.update_project(project_id, {
            "status": proj_data["status"],
            "github_repo_url": proj_data.get("github_repo_url"),
            "health_score": 85 if proj_data["status"] == "completed" else 70,
        })

        print(f"Created project: {proj_data['title']}")

        # Add updates with backdated timestamps
        created_updates = []
        for utype, content, days_ago in updates_spec:
            ts = (now + timedelta(days=days_ago)).isoformat()
            update = {
                "project_id": project_id,
                "user_id": user_id,
                "content": content,
                "update_type": utype,
                "ai_summary": "",
                "metadata": {},
            }
            resp = supabase.table("updates").insert({**update, "created_at": ts}).execute()
            created_updates.append(resp.data[0])
            print(f"  + {utype}: {content[:60]}...")

        # Create 3 snapshots spread over the timeline
        milestones = [u for u in created_updates if u["update_type"] == "milestone"]
        snap_targets = milestones[:3] if len(milestones) >= 3 else created_updates[::max(1, len(created_updates)//3)][:3]

        for i, update in enumerate(snap_targets):
            snap_title = f"Snapshot #{i+1} — {update['created_at'][:10]}"
            state = {
                "project": db.get_project(project_id),
                "updates": [u for u in created_updates if u["created_at"] <= update["created_at"]],
                "integrations": {},
                "collaborators": [],
                "metadata": {"snapshot_version": "1.0", "captured_at": update["created_at"]},
            }
            supabase.table("snapshots").insert({
                "project_id": project_id,
                "created_by": user_id,
                "title": snap_title,
                "snapshot_data": state,
                "ai_narrative": f"At this point, {update['content'][:150]}",
                "trigger": "milestone",
                "created_at": update["created_at"],
            }).execute()
            print(f"  📸 Snapshot: {snap_title}")

        print(f"  ✅ {proj_data['title']} seeded with {len(updates_spec)} updates and {len(snap_targets)} snapshots\n")

    print("✅ Demo data seeded successfully!")
    print(f"   Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
