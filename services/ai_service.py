from __future__ import annotations
import os
import sys
import json
import subprocess
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Always load from the project root .env, regardless of cwd
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

MODEL_GROQ = "llama-3.3-70b-versatile"
EMBED_MODEL = "text-embedding-3-small"


# ── Bulletproof groq import — installs itself if missing ─────────────────────

def _ensure_groq():
    try:
        import groq as _groq
        return _groq
    except ImportError:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "groq", "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        import groq as _groq
        return _groq


# ── Provider detection ────────────────────────────────────────────────────────

def _groq_key() -> str:
    return st.session_state.get("groq_key") or os.getenv("GROQ_API_KEY", "")

def _openai_key() -> str:
    return st.session_state.get("openai_key") or os.getenv("OPENAI_API_KEY", "")


def _provider() -> str:
    if _groq_key() and not _groq_key().startswith("your_"):
        return "groq"
    return "none"


def _openai():
    import openai
    return openai.OpenAI(api_key=_openai_key())


# ── Core generation ───────────────────────────────────────────────────────────

def _is_rate_error(e: Exception) -> bool:
    s = str(e)
    return "429" in s or "rate" in s.lower() or "quota" in s.lower()


def _generate_groq(system_text: str, user_text: str, max_tokens: int = 800) -> str:
    groq = _ensure_groq()
    key = _groq_key()
    if not key or key.startswith("your_"):
        raise RuntimeError("NO_AI_KEY")
    client = groq.Groq(api_key=key)
    completion = client.chat.completions.create(
        model=MODEL_GROQ,
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content.strip()


def _generate(system_text: str, user_text: str, max_tokens: int = 800) -> str:
    """Single entry point for all AI generation. Only uses Groq."""
    try:
        return _generate_groq(system_text, user_text, max_tokens)
    except RuntimeError:
        raise
    except Exception as e:
        if _is_rate_error(e):
            raise RuntimeError("Groq rate limit — wait a moment and try again.") from e
        raise RuntimeError(f"Groq error: {str(e)[:200]}") from e


def _active_model() -> str:
    return MODEL_GROQ if _provider() == "groq" else "none"


def ai_available() -> bool:
    try:
        _generate("Reply with one word.", "ping", max_tokens=5)
        return True
    except Exception:
        return False


def check_provider_status() -> dict:
    results = {}
    groq_key = _groq_key()
    if groq_key and not groq_key.startswith("your_"):
        key_hint = f"key: {groq_key[:4]}…{groq_key[-4:]}"
        try:
            _generate_groq("Reply with one word.", "ping", max_tokens=5)
            results["groq"] = {"ok": True, "label": "Groq (Llama 3.3 70B)", "detail": f"Active ({key_hint})"}
        except Exception as e:
            if _is_rate_error(e):
                results["groq"] = {"ok": False, "label": "Groq (Llama 3.3 70B)",
                    "detail": f"Rate limited — retry in a moment ({key_hint})"}
            else:
                results["groq"] = {"ok": False, "label": "Groq (Llama 3.3 70B)",
                    "detail": f"Error: {str(e)[:80]}"}
    else:
        results["groq"] = {"ok": False, "label": "Groq (Llama 3.3 70B)",
            "detail": "Not configured — free at console.groq.com/keys"}

    if _openai_key() and not _openai_key().startswith("your_"):
        try:
            _openai().models.list()
            results["openai"] = {"ok": True, "label": "OpenAI (embeddings)", "detail": "Active"}
        except Exception as e:
            results["openai"] = {"ok": False, "label": "OpenAI (embeddings)", "detail": f"Error: {str(e)[:80]}"}
    else:
        results["openai"] = {"ok": False, "label": "OpenAI (embeddings)",
            "detail": "Not configured — search uses text fallback"}

    return results


def _no_ai_msg() -> str:
    return (
        "AI features require a Groq API key. "
        "Get one free at console.groq.com/keys and add it as "
        "GROQ_API_KEY in your .env file, then restart the app."
    )


# ── Update summary ────────────────────────────────────────────────────────────

def summarize_update(content: str, update_type: str, project_title: str) -> str:
    try:
        return _generate(
            "You are ProjectVault's AI assistant. Generate a single concise sentence "
            "(max 20 words) summarizing the key insight from a project update. Be specific, not generic.",
            f"Project: {project_title}\nUpdate type: {update_type}\nContent: {content}\n\nOne-sentence summary:",
            max_tokens=120,
        )
    except Exception:
        return ""


# ── Snapshot narrative ────────────────────────────────────────────────────────

SNAPSHOT_SYSTEM = """You are ProjectVault's AI analyst. Given project state changes between two snapshots, generate a concise, insightful narrative (3-5 sentences) that explains:
1. What changed
2. Why it likely changed (infer from context)
3. What this means for the project going forward

Be specific, professional, and actionable. Reference concrete details from the data."""


def generate_snapshot_narrative(before: dict, after: dict) -> str:
    try:
        before_str = json.dumps(before, indent=2, default=str)[:3000]
        after_str = json.dumps(after, indent=2, default=str)[:3000]
        return _generate(
            SNAPSHOT_SYSTEM,
            f"BEFORE:\n{before_str}\n\nAFTER:\n{after_str}\n\nNarrative:",
            max_tokens=400,
        )
    except Exception:
        return "Snapshot captured. AI narrative generation pending."


# ── Health score ──────────────────────────────────────────────────────────────

HEALTH_SYSTEM = """You are ProjectVault's AI health analyst. Analyze project data and return a JSON object with:
- score: integer 0-100
- explanation: one sentence explaining the score
- signals: list of 2-3 specific signals that affected the score

Consider: recency of updates, presence of blockers, milestone completion, activity velocity, number of pivots.
Return ONLY valid JSON, no markdown."""


def calculate_health_score(project_data: dict) -> tuple[int, str]:
    try:
        raw = _generate(HEALTH_SYSTEM, json.dumps(project_data, indent=2, default=str)[:4000], max_tokens=300)
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group() if match else raw)
        return int(result.get("score", 70)), result.get("explanation", "")
    except Exception:
        return 70, "Health score could not be calculated."


# ── Retrospective ─────────────────────────────────────────────────────────────

RETRO_SYSTEM = """You are a senior project manager AI. Analyze project data and generate a structured retrospective.
Return ONLY a valid JSON object with these exact keys:
{
  "executive_summary": "2-3 sentences",
  "went_well": ["bullet with evidence", ...],
  "didnt_work": ["bullet with evidence", ...],
  "key_decisions": [{"decision": "...", "date": "...", "impact": "..."}, ...],
  "patterns_risks": ["cross-project insight or risk", ...],
  "recommendations": ["actionable recommendation", ...]
}
Be evidence-based. Reference actual data from updates, commits, and decisions."""


def generate_retrospective(project_data: dict) -> dict:
    _empty: dict = {
        "executive_summary": "",
        "went_well": [], "didnt_work": [],
        "key_decisions": [], "patterns_risks": [], "recommendations": [],
    }
    try:
        raw = _generate(RETRO_SYSTEM, json.dumps(project_data, indent=2, default=str)[:6000], max_tokens=2000)
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(match.group() if match else raw)
    except Exception as e:
        _empty["executive_summary"] = f"Retrospective generation failed: {e}"
        return _empty


# ── Project Q&A chat ──────────────────────────────────────────────────────────

def chat_with_project(messages: list[dict], project_context: dict) -> str:
    context_str = json.dumps(project_context, indent=2, default=str)[:8000]
    system_text = (
        "You are ProjectVault's AI assistant for a specific project. "
        "Answer questions based ONLY on the project data provided. "
        "If information isn't in the data, say so.\n\nPROJECT DATA:\n" + context_str
    )
    last_user = messages[-1]["content"] if messages else ""
    history_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages[:-1]
    )
    user_text = f"{history_text}\nUser: {last_user}" if history_text else last_user
    try:
        return _generate(system_text, user_text, max_tokens=800)
    except Exception as e:
        msg = str(e).lower()
        if "no_ai_key" in msg:
            return "No AI key configured. Add GROQ_API_KEY to your .env file."
        if "rate" in msg or "quota" in msg:
            return "Groq rate limit — please wait a moment and try again."
        return f"AI unavailable: {str(e)[:120]}"


# ── Snapshot comparison ───────────────────────────────────────────────────────

def compare_snapshots_ai(snap_a: dict, snap_b: dict) -> str:
    try:
        a_str = json.dumps(snap_a.get("snapshot_data", {}), indent=2, default=str)[:3000]
        b_str = json.dumps(snap_b.get("snapshot_data", {}), indent=2, default=str)[:3000]
        return _generate(
            "You are a project analyst. Compare two project snapshots and highlight key differences clearly.",
            f"SNAPSHOT A ({snap_a.get('created_at', '')[:10]}):\n{a_str}\n\n"
            f"SNAPSHOT B ({snap_b.get('created_at', '')[:10]}):\n{b_str}\n\n"
            "Provide a structured comparison covering: what changed, what was added, what was removed, and significance.",
            max_tokens=600,
        )
    except Exception:
        return "Comparison unavailable."


# ── Embeddings ────────────────────────────────────────────────────────────────

def generate_embedding(text: str) -> list[float] | None:
    try:
        client = _openai()
        resp = client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
        return resp.data[0].embedding
    except Exception:
        return None


# ── Long document analysis ────────────────────────────────────────────────────

def analyze_long_document(content: str, question: str) -> str:
    try:
        return _generate("You are a document analyst.", f"{question}\n\nDocument:\n{content}", max_tokens=1000)
    except Exception as e:
        return f"Analysis failed: {e}"
