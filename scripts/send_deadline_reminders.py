"""Send deadline reminder emails (T-7, T-2, T-0) for projects and checklist items.

Runs daily via GitHub Actions. Idempotent — uses reminder_log to avoid duplicates.

Required env vars:
  SUPABASE_URL, SUPABASE_SERVICE_KEY  (admin client; bypasses RLS)
  RESEND_API_KEY                      (or SMTP_HOST/SMTP_USER/SMTP_PASSWORD)
  APP_URL                             (optional, link in email)
  DIGEST_FROM_EMAIL                   (optional, sender address)
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client


REMINDER_OFFSETS = [7, 2, 0]  # days before deadline


def _admin():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
    return create_client(url, key)


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)[:10]).date()
    except Exception:
        return None


def _already_sent(client, target_type: str, target_id: str, days_before: int) -> bool:
    res = (
        client.table("reminder_log")
        .select("id")
        .eq("target_type", target_type)
        .eq("target_id", target_id)
        .eq("days_before", days_before)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def _record_sent(client, user_id: str, target_type: str, target_id: str, days_before: int) -> None:
    try:
        client.table("reminder_log").insert({
            "user_id": user_id,
            "target_type": target_type,
            "target_id": target_id,
            "days_before": days_before,
        }).execute()
    except Exception as e:
        print(f"  ! failed to log reminder: {e}")


def _send_email(to: str, subject: str, html: str) -> bool:
    # Resend
    api_key = os.getenv("RESEND_API_KEY", "")
    if api_key:
        try:
            import resend
            resend.api_key = api_key
            from_addr = os.getenv("DIGEST_FROM_EMAIL", "ProjectVault <digest@projectvault.app>")
            resend.Emails.send({"from": from_addr, "to": [to], "subject": subject, "html": html})
            return True
        except Exception as e:
            print(f"  ! resend failed: {e}")

    # SMTP fallback
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
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
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(user, password)
            s.sendmail(from_addr, [to], msg.as_string())
        return True
    except Exception as e:
        print(f"  ! smtp failed: {e}")
        return False


def _build_html(user_name: str, kind: str, target_title: str, project_title: str,
                deadline: date, days_before: int) -> str:
    if days_before == 0:
        urgency_label = "Due today"
        accent = "#A8311F"
    elif days_before <= 2:
        urgency_label = f"Due in {days_before} day{'s' if days_before != 1 else ''}"
        accent = "#A8311F"
    else:
        urgency_label = f"Due in {days_before} days"
        accent = "#8A6A1F"

    app_url = os.getenv("APP_URL", "https://projectvault.streamlit.app")
    label = "Project" if kind == "project" else "Checklist item"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'></head>
<body style='background:#FAF6F2; color:#2C1810; font-family:system-ui,sans-serif; margin:0; padding:0;'>
  <div style='max-width:560px; margin:0 auto; padding:40px 24px;'>
    <div style='text-align:center; margin-bottom:24px;'>
      <div style='font-size:1.5rem; font-weight:800; color:#2C1810;'>🔐 ProjectVault</div>
      <div style='color:#A88F87; font-size:0.85rem; margin-top:4px;'>Deadline reminder</div>
    </div>

    <h1 style='font-size:1.3rem; margin-bottom:4px;'>Hi {user_name},</h1>
    <p style='color:#6B4A3E; margin-top:4px;'>This is a heads-up on an upcoming deadline.</p>

    <div style='background:#FFFFFF; border:1px solid rgba(142,94,78,0.15); border-radius:12px; padding:20px; margin:20px 0;'>
      <div style='color:#A88F87; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.1em; font-weight:600; margin-bottom:8px;'>{label}</div>
      <div style='font-size:1.15rem; font-weight:700; color:#2C1810; margin-bottom:6px;'>{target_title}</div>
      {"<div style='color:#6B4A3E; font-size:0.9rem; margin-bottom:12px;'>in <b>" + project_title + "</b></div>" if kind == "checklist" else ""}
      <div style='display:inline-block; padding:6px 14px; border-radius:999px; background:rgba(207,111,97,0.12); color:{accent}; font-weight:700; font-size:0.85rem;'>
        {urgency_label} · {deadline.strftime('%b %d, %Y')}
      </div>
    </div>

    <div style='text-align:center; margin-top:32px;'>
      <a href='{app_url}' style='display:inline-block; background:#2C1810; color:#FAF6F2; padding:10px 22px; border-radius:8px; text-decoration:none; font-weight:600;'>Open ProjectVault</a>
    </div>

    <div style='text-align:center; margin-top:32px; color:#A88F87; font-size:0.75rem;'>
      You're receiving this because a deadline you set is coming up.
    </div>
  </div>
</body>
</html>"""


def _process_projects(client) -> int:
    today = date.today()
    sent = 0
    # Fetch active/paused projects with a deadline
    projects = (
        client.table("projects")
        .select("id,title,deadline,owner_id,status")
        .in_("status", ["active", "paused"])
        .not_.is_("deadline", "null")
        .execute().data or []
    )
    for p in projects:
        dl = _parse_date(p.get("deadline"))
        if not dl:
            continue
        days = (dl - today).days
        if days not in REMINDER_OFFSETS:
            continue
        if _already_sent(client, "project", p["id"], days):
            continue

        owner = client.table("users").select("id,email,name").eq("id", p["owner_id"]).limit(1).execute().data
        if not owner:
            continue
        owner = owner[0]
        email = owner.get("email")
        if not email:
            continue
        name = owner.get("name") or email.split("@")[0]

        subject = f"⏰ {p['title']} — due in {days} day{'s' if days != 1 else ''}" if days > 0 else f"⏰ {p['title']} — due today"
        html = _build_html(name, "project", p["title"], p["title"], dl, days)
        print(f"  → project '{p['title']}' (T-{days}) to {email}")
        if _send_email(email, subject, html):
            _record_sent(client, owner["id"], "project", p["id"], days)
            sent += 1
        else:
            print(f"    ! send failed")
    return sent


def _process_checklists(client) -> int:
    today = date.today()
    sent = 0
    items = (
        client.table("checklists")
        .select("id,title,deadline,project_id,is_done")
        .eq("is_done", False)
        .not_.is_("deadline", "null")
        .execute().data or []
    )
    if not items:
        return 0

    project_ids = list({i["project_id"] for i in items})
    projects_by_id = {
        p["id"]: p for p in (
            client.table("projects")
            .select("id,title,owner_id,status")
            .in_("id", project_ids)
            .execute().data or []
        )
    }

    for i in items:
        dl = _parse_date(i.get("deadline"))
        if not dl:
            continue
        days = (dl - today).days
        if days not in REMINDER_OFFSETS:
            continue
        if _already_sent(client, "checklist", i["id"], days):
            continue

        proj = projects_by_id.get(i["project_id"])
        if not proj or proj.get("status") not in ("active", "paused"):
            continue

        owner = client.table("users").select("id,email,name").eq("id", proj["owner_id"]).limit(1).execute().data
        if not owner:
            continue
        owner = owner[0]
        email = owner.get("email")
        if not email:
            continue
        name = owner.get("name") or email.split("@")[0]

        subject = f"⏰ {i['title']} — due in {days} day{'s' if days != 1 else ''}" if days > 0 else f"⏰ {i['title']} — due today"
        html = _build_html(name, "checklist", i["title"], proj["title"], dl, days)
        print(f"  → checklist '{i['title']}' (T-{days}) to {email}")
        if _send_email(email, subject, html):
            _record_sent(client, owner["id"], "checklist", i["id"], days)
            sent += 1
        else:
            print(f"    ! send failed")
    return sent


def main():
    client = _admin()
    print(f"[{datetime.utcnow().isoformat()}Z] Running deadline reminders (offsets: {REMINDER_OFFSETS})")
    p_sent = _process_projects(client)
    c_sent = _process_checklists(client)
    print(f"Done. Sent {p_sent} project + {c_sent} checklist reminders.")


if __name__ == "__main__":
    main()
