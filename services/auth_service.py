import os
import streamlit as st
from supabase import create_client, Client
from functools import lru_cache


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """Service-role client — bypasses RLS. Only for server-side writes."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


def sign_up(email: str, password: str, name: str):
    supabase = get_supabase()
    response = supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"name": name, "full_name": name}},
    })
    return response


def sign_in(email: str, password: str):
    supabase = get_supabase()
    return supabase.auth.sign_in_with_password({"email": email, "password": password})


def sign_in_with_google(redirect_url: str) -> str:
    """Returns the Google OAuth URL to redirect the user to."""
    supabase = get_supabase()
    response = supabase.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {
            "redirect_to": redirect_url,
            "flow_type": "pkce",
        },
    })
    return response.url


def exchange_code_for_session(code: str):
    """Exchange OAuth PKCE code for a session after Google redirect."""
    supabase = get_supabase()
    return supabase.auth.exchange_code_for_session({"auth_code": code})


def restore_session(access_token: str, refresh_token: str) -> dict | None:
    """
    Validate stored tokens and restore session. Returns user dict or None.
    Tries set_session first; if the access token is expired, falls back to refresh.
    """
    supabase = get_supabase()
    try:
        response = supabase.auth.set_session(access_token, refresh_token)
        if response.user and response.session:
            return {
                "user": {
                    "id": str(response.user.id),
                    "email": response.user.email,
                    "name": (
                        response.user.user_metadata.get("name")
                        or response.user.user_metadata.get("full_name")
                        or response.user.email
                    ),
                },
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
            }
    except Exception:
        pass

    # Access token may be expired — try refresh
    try:
        response = supabase.auth.refresh_session(refresh_token)
        if response.user and response.session:
            return {
                "user": {
                    "id": str(response.user.id),
                    "email": response.user.email,
                    "name": (
                        response.user.user_metadata.get("name")
                        or response.user.user_metadata.get("full_name")
                        or response.user.email
                    ),
                },
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
            }
    except Exception:
        pass

    return None


def sign_out() -> None:
    supabase = get_supabase()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for key in ["user", "access_token", "refresh_token", "current_project", "chat_history"]:
        st.session_state.pop(key, None)


def get_current_user():
    supabase = get_supabase()
    try:
        return supabase.auth.get_user()
    except Exception:
        return None


def require_auth():
    if "user" not in st.session_state or not st.session_state.get("user"):
        st.switch_page("pages/1_login.py")


def _set_session_from_response(response) -> bool:
    if response.user and response.session:
        st.session_state.user = {
            "id": str(response.user.id),
            "email": response.user.email,
            "name": (
                response.user.user_metadata.get("name")
                or response.user.user_metadata.get("full_name")
                or response.user.email
            ),
        }
        st.session_state.access_token = response.session.access_token
        st.session_state.refresh_token = response.session.refresh_token or ""
        return True
    return False


def _ensure_user_profile(response) -> None:
    try:
        supabase = get_supabase()
        user = response.user
        supabase.table("users").upsert({
            "id": str(user.id),
            "email": user.email,
            "name": (
                user.user_metadata.get("name")
                or user.user_metadata.get("full_name")
                or user.email
            ),
            "avatar_url": user.user_metadata.get("avatar_url"),
        }, on_conflict="id").execute()
    except Exception:
        pass


def handle_login(email: str, password: str) -> tuple[bool, str]:
    try:
        response = sign_in(email, password)
        if _set_session_from_response(response):
            _ensure_user_profile(response)
            return True, ""
        return False, "Invalid credentials."
    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg:
            return False, "Invalid email or password."
        if "Email not confirmed" in msg:
            return False, "Please confirm your email first. Check your inbox."
        return False, f"Login failed: {msg}"


def handle_signup(email: str, password: str, name: str) -> tuple[bool, str]:
    try:
        response = sign_up(email, password, name)
        if response.user:
            if response.session:
                _set_session_from_response(response)
                _ensure_user_profile(response)
            return True, ""
        return False, "Signup failed. Please try again."
    except Exception as e:
        msg = str(e)
        if "already registered" in msg or "User already registered" in msg:
            return False, "An account with this email already exists. Try signing in."
        if "Password should be" in msg or "password" in msg.lower():
            return False, "Password must be at least 6 characters."
        return False, f"Signup failed: {msg}"


def handle_oauth_callback() -> tuple[bool, str]:
    """Call on every page load to handle Google OAuth redirect."""
    code = st.query_params.get("code")
    if not code:
        return False, ""
    try:
        response = exchange_code_for_session(code)
        # Clear the code from URL
        st.query_params.clear()
        if _set_session_from_response(response):
            _ensure_user_profile(response)
            return True, ""
        return False, "OAuth login failed. Please try again."
    except Exception as e:
        st.query_params.clear()
        return False, f"OAuth error: {e}"
