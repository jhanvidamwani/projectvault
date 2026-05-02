from __future__ import annotations
import os
import json
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from services.auth_service import get_supabase
from services import ai_service as ai



# ── HTML template ─────────────────────────────────────────────────────────────

def _build_html(user_name: str, stale: list[dict], risk_summary: str, health_score: int) -> str:
    stale_rows = "".join(
        f"<tr><td style='padding:8px 12px; border-bottom:1px solid #2c2c2c;'>{p['title']}</td>"
        f"<td style='padding:8px 12px; border-bottom:1px solid #2c2c2c; color:#c47a6a;'>{p['days_stale']}d ago</td></tr>"
        for p in stale
    )
    stale_section = f"""
    <h2 style='color:#c47a6a; margin-top:32px;'>Needs Attention</h2>
    <table style='width:100%; border-collapse:collapse; background:#252525; border-radius:8px; overflow:hidden;'>
      <thead>
        <tr style='background:#2c2c2c;'>
          <th style='padding:10px 12px; text-align:left; color:#999999;'>Project</th>
          <th style='padding:10px 12px; text-align:left; color:#999999;'>Last Update</th>
        </tr>
      </thead>
      <tbody>{stale_rows}</tbody>
    </table>""" if stale else "<p style='color:#8ab5a0;'>All projects updated recently. Great work!</p>"

    score_color = "#8ab5a0" if health_score >= 70 else "#c4a882" if health_score >= 40 else "#c47a6a"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'></head>
<body style='background:#1e1e1e; color:#f0f0f0; font-family:system-ui,sans-serif; margin:0; padding:0;'>
  <div style='max-width:600px; margin:0 auto; padding:40px 24px;'>
    <div style='text-align:center; margin-bottom:32px;'>
      <div style='font-size:2rem; font-weight:800; color:#253245;'>🔐 ProjectVault</div>
      <div style='color:#666666; font-size:0.9rem; margin-top:4px;'>Weekly Digest</div>
    </div>

    <h1 style='font-size:1.4rem; margin-bottom:4px;'>Good morning, {user_name}!</h1>
    <p style='color:#666666;'>Here's your project portfolio summary for the week.</p>

    <div style='background:#252525; border-radius:12px; padding:20px; text-align:center; margin:24px 0;'>
      <div style='color:#999999; font-size:0.85rem; margin-bottom:4px;'>Portfolio Health Score</div>
      <div style='font-size:3rem; font-weight:800; color:{score_color};'>{health_score}</div>
      <div style='color:#666666; font-size:0.8rem;'>/ 100</div>
    </div>

    {stale_section}

    <h2 style='color:#253245; margin-top:32px;'>AI Risk Summary</h2>
    <div style='background:#252525; border-radius:8px; padding:16px; color:#333333; line-height:1.6;'>
      {risk_summary.replace(chr(10), '<br>')}
    </div>

    <div style='text-align:center; margin-top:40px; color:#2c2c2c; font-size:0.8rem;'>
      <a href='{os.getenv("APP_URL", "http://localhost:8501")}' style='color:#253245;'>Open ProjectVault</a>
      &nbsp;·&nbsp;
      You're receiving this because weekly digest is enabled in your account settings.
    </div>
  </div>
</body>
</html>"""


# ── AI cross-project risk summary ─────────────────────────────────────────────

def _generate_risk_summary(projects: list[dict]) -> str:
    try:
        data_str = json.dumps(
            [{"title": p.get("title"), "status": p.get("status"), "health_score": p.get("health_score"),
              "health_explanation": p.get("health_explanation")} for p in projects[:15]],
            indent=2,
        )[:3000]
        return ai._generate(
            "You are ProjectVault's AI. Given a list of projects, write a 2-3 sentence cross-project risk summary for a weekly digest email. Be specific about patterns you see. Plain text only, no markdown.",
            data_str,
            max_tokens=300,
        )
    except Exception:
        return "Unable to generate AI risk summary this week."


def _portfolio_health_score(projects: list[dict]) -> int:
    scores = [p.get("health_score") or 70 for p in projects if p.get("health_score")]
    return int(sum(scores) / len(scores)) if scores else 70


# ── Send via Resend ───────────────────────────────────────────────────────────

def _send_resend(to: str, subject: str, html: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        return False
    try:
        import resend
        resend.api_key = api_key
        from_addr = os.getenv("DIGEST_FROM_EMAIL", "ProjectVault <digest@projectvault.app>")
        resend.Emails.send({"from": from_addr, "to": [to], "subject": subject, "html": html})
        return True
    except Exception:
        return False


def _send_smtp(to: str, subject: str, html: str) -> bool:
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", user)
    if not (host and user and password):
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to], msg.as_string())
        return True
    except Exception:
        return False


def send_email(to: str, subject: str, html: str) -> bool:
    return _send_resend(to, subject, html) or _send_smtp(to, subject, html)


# ── Per-user digest ───────────────────────────────────────────────────────────

def send_digest_for_user(user_row: dict) -> bool:
    supabase = get_supabase()
    user_id = user_row["id"]
    email = user_row.get("email", "")
    name = user_row.get("name") or email

    owned = supabase.table("projects").select("*").eq("owner_id", user_id).execute().data or []
    if not owned:
        return False

    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(days=7)
    stale = []
    for p in owned:
        try:
            updated = datetime.fromisoformat(p["updated_at"].replace("Z", "+00:00"))
            if updated < stale_threshold:
                stale.append({**p, "days_stale": (now - updated).days})
        except Exception:
            pass

    risk_summary = _generate_risk_summary(owned)
    health = _portfolio_health_score(owned)
    html = _build_html(name, stale, risk_summary, health)
    subject = f"Your Weekly ProjectVault Digest — {now.strftime('%b %d')}"

    sent = send_email(email, subject, html)
    if sent:
        supabase.table("users").update({
            "last_digest_sent": now.isoformat()
        }).eq("id", user_id).execute()
    return sent


# ── Scheduler entry point ─────────────────────────────────────────────────────

def send_weekly_digests() -> None:
    supabase = get_supabase()
    users = supabase.table("users").select("id, email, name, digest_enabled, last_digest_sent").eq("digest_enabled", True).execute().data or []
    for user_row in users:
        try:
            send_digest_for_user(user_row)
        except Exception:
            pass


def start_scheduler() -> None:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        send_weekly_digests,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_digest",
        replace_existing=True,
    )
    scheduler.start()
