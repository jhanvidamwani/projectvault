from __future__ import annotations
import io
import json
import re
import time
from services import ai_service as ai, db_service as db

REPORT_SYSTEM = """You are a senior project analyst producing a professional written report. Given project data, write a clear, substantive analysis report. Think like a consultant summarizing this work for stakeholders.

Write the report in this structure:

# [Project Name] — Analysis Report

## Summary
3–4 sentences: what this project is, what it set out to do, and where it stands today.

## What Was Accomplished
Specific, concrete list of what was built, shipped, or completed. Reference actual update content — not generic phrases. Use bullet points.

## Key Decisions & Technical Approach
The significant choices made during this project — architecture, tools, pivots, strategy changes. Reference decision-type updates and milestones. Explain the reasoning where visible in the data.

## Challenges & How They Were Handled
Specific blockers, problems, and obstacles that appeared. What was done about each. Reference blocker-type updates and pivots.

## Collaboration & Team
How the work was organized. Solo or team. Who contributed. Working patterns if visible.

## Health & Risk Assessment
**Health Score: X/100**
Honest assessment of project health based on the data — momentum, blockers, recent activity, completion status.

## Recommended Next Steps
3–5 specific, actionable items based on what's open, what's at risk, and what the data shows.

Rules:
- Be specific. Name actual things from the data, not generic placeholders.
- Write in clear professional prose (not overly formal).
- Do not mention AI tools, models, or analysis software.
- Do not include a "Timeline" section.
- If a section has no relevant data, write one honest sentence saying so."""

ANALYSIS_SYSTEM = """You are ProjectVault's AI analyst. Analyze project data and return ONLY a valid JSON object with exactly these 4 keys:
{
  "velocity_trend": {
    "insight": "One specific sentence about update frequency trend with a concrete number or observation",
    "detail": "Supporting statistic e.g. X updates in last 7 days vs Y the week before",
    "status": "green|yellow|red"
  },
  "scope_analysis": {
    "insight": "One specific sentence about how project scope has evolved",
    "detail": "Supporting observation about pivots, description changes, or growth",
    "status": "green|yellow|red"
  },
  "collaboration_pattern": {
    "insight": "One specific sentence about team activity or solo work patterns",
    "detail": "Supporting detail about timing or team size",
    "status": "green|yellow|red"
  },
  "predictive_completion": {
    "insight": "One specific sentence about trajectory or estimated completion",
    "detail": "Basis for this prediction from current velocity",
    "status": "green|yellow|red"
  }
}
Base everything on actual data. Return ONLY valid JSON, no markdown."""

_analysis_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 3600


def generate_report(project_id: str) -> str:
    project = db.get_project(project_id)
    if not project:
        return "Project not found."

    updates = db.get_updates(project_id, limit=100)
    snapshots = db.get_snapshots(project_id)
    collaborators = db.get_collaborators(project_id)

    project_data: dict = {
        "title": project.get("title"),
        "description": project.get("description"),
        "status": project.get("status"),
        "health_score": project.get("health_score"),
        "health_explanation": project.get("health_explanation"),
        "tags": project.get("tags"),
        "github_repo_url": project.get("github_repo_url"),
        "created_at": project.get("created_at", "")[:10],
        "team_size": len(collaborators),
        "updates": [
            {
                "content": u.get("content"),
                "type": u.get("update_type"),
                "date": u.get("created_at", "")[:10],
                "ai_summary": u.get("ai_summary"),
            }
            for u in updates
        ],
        "snapshots": [
            {
                "title": s.get("title"),
                "narrative": s.get("ai_narrative"),
                "date": s.get("created_at", "")[:10],
                "trigger": s.get("trigger"),
            }
            for s in snapshots
        ],
    }

    try:
        from services import links_service
        links = links_service.get_project_links(project_id)
        if links:
            project_data["linked_tools"] = [
                f"{l.get('icon', '')} {l.get('platform', '')} — {l.get('label', '')}"
                for l in links
            ]
    except Exception:
        pass

    try:
        data_str = json.dumps(project_data, indent=2, default=str)[:8000]
        return ai._generate(REPORT_SYSTEM, f"Write the analysis report:\n\n{data_str}", max_tokens=3000)
    except Exception as e:
        e_str = str(e)
        if "NO_AI_KEY" in e_str:
            return _template_report(project, updates, snapshots, collaborators)
        # AI configured but call failed — show error + basic report
        banner = f"> ⚠️ AI report generation failed: {e_str[:200]}\n\n---\n\n"
        return banner + _template_report(project, updates, snapshots, collaborators)


def _template_report(project: dict, updates: list, snapshots: list, collaborators: list) -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = project.get("title", "Untitled Project")
    desc = project.get("description") or "No description provided."
    status = project.get("status", "unknown").capitalize()
    created = (project.get("created_at") or "")[:10]
    health = project.get("health_score", "—")

    # Count update types
    update_type_counts: dict[str, int] = {}
    for u in updates:
        t = u.get("update_type", "note")
        update_type_counts[t] = update_type_counts.get(t, 0) + 1

    milestones = [u for u in updates if u.get("update_type") == "milestone"]
    decisions = [u for u in updates if u.get("update_type") == "decision"]
    blockers = [u for u in updates if u.get("update_type") == "blocker"]
    pivots = [u for u in updates if u.get("update_type") == "pivot"]

    milestone_lines = "\n".join(
        f"- {u.get('content','')[:140]} *({(u.get('created_at') or '')[:10]})*"
        for u in milestones[:8]
    ) or "_No milestones recorded._"

    decision_lines = "\n".join(
        f"- {u.get('content','')[:140]} *({(u.get('created_at') or '')[:10]})*"
        for u in decisions[:8]
    ) or "_No decisions recorded._"

    blocker_lines = "\n".join(
        f"- {u.get('content','')[:140]}"
        for u in blockers[:5]
    ) or "_No blockers recorded._"

    collab_names = []
    for c in collaborators:
        u_info = c.get("users") or {}
        name = u_info.get("name") or u_info.get("email") or "Unknown"
        collab_names.append(f"{name} ({c.get('role','viewer')})")
    team_str = ", ".join(collab_names) if collab_names else "Solo project"

    recent_updates = "\n".join(
        f"- **[{u.get('update_type','note').upper()}]** {u.get('content','')[:120]} *{(u.get('created_at') or '')[:10]}*"
        for u in updates[:12]
    ) or "_No updates yet._"

    return f"""# {title} — Analysis Report
_Generated: {now}_

## Summary
{desc}

**Status:** {status} · **Created:** {created} · **Health Score:** {health}/100 · **Team:** {team_str}

## What Was Accomplished

{milestone_lines}

**Activity breakdown:** {len(updates)} total updates — {', '.join(f'{v} {k}{"s" if v>1 else ""}' for k, v in update_type_counts.items()) or "none recorded"}.

## Key Decisions

{decision_lines}

## Challenges

{blocker_lines}
{f'{chr(10)}_Pivots recorded: {len(pivots)}_' if pivots else ''}

## Collaboration & Team

{team_str}. {len(snapshots)} snapshot(s) captured across the project lifetime.

## Health Assessment

**Health Score: {health}/100**

{project.get('health_explanation') or 'Health score based on project activity, recency of updates, and milestone completion.'}

## Recent Activity

{recent_updates}

---
_Add a Groq API key (free at console.groq.com/keys) as GROQ\\_API\\_KEY in your .env to generate full AI-powered reports._"""


def generate_deep_analysis(project_id: str) -> dict:
    now = time.time()
    if project_id in _analysis_cache:
        ts, cached = _analysis_cache[project_id]
        if now - ts < _CACHE_TTL:
            return cached

    project = db.get_project(project_id)
    updates = db.get_updates(project_id, limit=100)
    snapshots = db.get_snapshots(project_id)
    collaborators = db.get_collaborators(project_id)

    from datetime import datetime, timezone
    now_dt = datetime.now(timezone.utc)

    parsed_updates = []
    for u in updates:
        try:
            created = datetime.fromisoformat(u["created_at"].replace("Z", "+00:00"))
            parsed_updates.append({
                "content": u.get("content", "")[:200],
                "type": u.get("update_type"),
                "days_ago": (now_dt - created).days,
                "weekday": created.strftime("%A"),
            })
        except Exception:
            pass

    last_7 = sum(1 for u in parsed_updates if u["days_ago"] <= 7)
    prev_7 = sum(1 for u in parsed_updates if 7 < u["days_ago"] <= 14)

    data = {
        "title": project.get("title"),
        "description": project.get("description"),
        "status": project.get("status"),
        "created_at": project.get("created_at", "")[:10],
        "total_updates": len(updates),
        "total_snapshots": len(snapshots),
        "total_collaborators": len(collaborators),
        "updates_last_7_days": last_7,
        "updates_prev_7_days": prev_7,
        "recent_updates": parsed_updates[:30],
    }

    # Try AI first
    try:
        raw = ai._generate(ANALYSIS_SYSTEM, json.dumps(data, indent=2, default=str)[:5000], max_tokens=1000)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group() if match else raw)
        _analysis_cache[project_id] = (now, result)
        return result
    except Exception:
        pass

    # Rule-based fallback — always produces meaningful insights
    result = _rule_based_analysis(project, parsed_updates, last_7, prev_7, snapshots, collaborators)
    _analysis_cache[project_id] = (now, result)
    return result


def _rule_based_analysis(
    project: dict,
    parsed_updates: list,
    last_7: int,
    prev_7: int,
    snapshots: list,
    collaborators: list,
) -> dict:
    total = len(parsed_updates)

    # ── Velocity Trend ────────────────────────────────────────────────────────
    if total == 0:
        velocity = {
            "insight": "No updates logged yet.",
            "detail": "Add your first project update to start tracking activity velocity.",
            "status": "blue",
        }
    elif total == 1:
        velocity = {
            "insight": "Project has 1 update logged.",
            "detail": "Add more updates over time to track velocity trends.",
            "status": "blue",
        }
    elif last_7 == 0 and total > 0:
        days_since = parsed_updates[0]["days_ago"] if parsed_updates else "?"
        velocity = {
            "insight": "No activity in the past 7 days.",
            "detail": f"Last update was {days_since} day(s) ago. Consider adding a status update.",
            "status": "red",
        }
    elif last_7 > prev_7:
        velocity = {
            "insight": f"Accelerating — {last_7} update(s) this week vs {prev_7} last week.",
            "detail": f"{total} total updates logged across the project lifetime.",
            "status": "green",
        }
    elif last_7 < prev_7:
        velocity = {
            "insight": f"Slowing down — {last_7} update(s) this week vs {prev_7} last week.",
            "detail": "Consider reviewing blockers or re-engaging with the project.",
            "status": "yellow",
        }
    else:
        velocity = {
            "insight": f"Steady pace — {last_7} update(s) per week.",
            "detail": f"{total} total updates logged.",
            "status": "yellow",
        }

    # ── Scope Analysis ────────────────────────────────────────────────────────
    desc = project.get("description") or ""
    word_count = len(desc.split()) if desc.strip() else 0
    pivot_count = sum(1 for u in parsed_updates if u.get("type") == "pivot")
    decision_count = sum(1 for u in parsed_updates if u.get("type") == "decision")

    if word_count == 0:
        scope = {
            "insight": "No project description added yet.",
            "detail": "Add a description in project Settings to document scope and goals.",
            "status": "blue",
        }
    elif pivot_count > 0:
        scope = {
            "insight": f"Scope has shifted — {pivot_count} pivot(s) recorded.",
            "detail": f"Description: {word_count} words · {decision_count} decision(s) logged.",
            "status": "yellow",
        }
    elif word_count < 20:
        scope = {
            "insight": f"Brief description: {word_count} word(s).",
            "detail": "Expand the description to better capture project scope and goals.",
            "status": "yellow",
        }
    else:
        scope = {
            "insight": f"Well-scoped — {word_count} word description with {decision_count} decision(s) logged.",
            "detail": f"{len(snapshots)} snapshot(s) taken. {pivot_count} pivot(s) recorded.",
            "status": "green",
        }

    # ── Collaboration Pattern ─────────────────────────────────────────────────
    collab_count = len(collaborators)
    if collab_count <= 1:
        collab = {
            "insight": "Solo project — you are the only contributor.",
            "detail": "Invite collaborators from the Settings tab to unlock team pattern analysis.",
            "status": "blue",
        }
    else:
        roles = {}
        for c in collaborators:
            r = c.get("role", "viewer")
            roles[r] = roles.get(r, 0) + 1
        role_str = " · ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in roles.items())
        collab = {
            "insight": f"Team of {collab_count} — {role_str}.",
            "detail": f"{last_7} update(s) logged this week across the team.",
            "status": "green",
        }

    # ── Predictive Completion ─────────────────────────────────────────────────
    target_date = project.get("target_date") or project.get("deadline")
    if total == 0:
        prediction = {
            "insight": "No activity to base a prediction on.",
            "detail": "Add project updates and set a target deadline to enable completion forecasting.",
            "status": "blue",
        }
    elif not target_date:
        avg_per_week = round((last_7 + prev_7) / 2, 1) if (last_7 + prev_7) > 0 else 0
        prediction = {
            "insight": "No target deadline set.",
            "detail": f"Current pace: ~{avg_per_week} update(s)/week. Set a deadline in Settings to enable forecasting.",
            "status": "blue",
        }
    else:
        from datetime import datetime
        try:
            deadline = datetime.fromisoformat(target_date)
            days_left = (deadline - datetime.now()).days
            avg = (last_7 + prev_7) / 2 if (last_7 + prev_7) > 0 else 0
            prediction = {
                "insight": f"{days_left} day(s) until deadline.",
                "detail": f"Current pace: ~{round(avg,1)} update(s)/week.",
                "status": "green" if days_left > 14 else "yellow" if days_left > 0 else "red",
            }
        except Exception:
            prediction = {
                "insight": "Deadline set but format unrecognised.",
                "detail": "Update your deadline in project Settings.",
                "status": "yellow",
            }

    return {
        "velocity_trend": velocity,
        "scope_analysis": scope,
        "collaboration_pattern": collab,
        "predictive_completion": prediction,
    }


def generate_pdf(report_md: str, project_title: str) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=inch, leftMargin=inch,
        topMargin=inch, bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=18, spaceAfter=14)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, spaceAfter=4)

    story = []
    for line in report_md.split("\n"):
        if line.startswith("# "):
            story.append(Paragraph(line[2:], h1))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], h2))
        elif line.startswith(("- ", "* ")):
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line[2:])
            story.append(Paragraph(f"• {clean}", body))
        elif line.strip():
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            clean = re.sub(r"\*(.+?)\*", r"\1", clean)
            story.append(Paragraph(clean, body))
        else:
            story.append(Spacer(1, 0.06 * inch))

    doc.build(story)
    return buffer.getvalue()
