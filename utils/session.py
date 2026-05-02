"""
Session persistence via browser cookies using stc.html().

Cookies are set ONLY at two moments:
  1. On successful login (in 1_login.py before switching pages)
  2. On session restore from query params (before st.rerun)

This prevents any stc.html() components from rendering on protected pages,
which avoids the visible code-block artifact on the dashboard.
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as stc


_COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days


def _set_cookie_js(name: str, value: str, max_age: int = _COOKIE_MAX_AGE) -> str:
    safe = value.replace("\\", "\\\\").replace("'", "\\'")
    return (
        f"document.cookie='{name}='+encodeURIComponent('{safe}')"
        f"+'; max-age={max_age}; path=/; SameSite=Lax';"
    )


_JS_RESTORE = """
(function(){
  function gc(n){
    var m=document.cookie.match(new RegExp('(?:^|;)\\s*'+n+'=([^;]*)'));
    return m?decodeURIComponent(m[1]):null;
  }
  var at=gc('pv_at'), rt=gc('pv_rt');
  if(at&&rt){
    var dest='/2_dashboard';
    try{
      if(window.parent.location.search.indexOf('pv_at=')!==-1)return;
      dest=window.parent.location.pathname;
    }catch(e){}
    window.parent.location.href=dest
      +'?pv_at='+encodeURIComponent(at)
      +'&pv_rt='+encodeURIComponent(rt);
  }else{
    window.parent.location.href='/1_login';
  }
})();
"""

_JS_LOGOUT = """
(function(){
  ['pv_at','pv_rt'].forEach(function(n){
    document.cookie=n+'=; max-age=0; path=/';
  });
  window.parent.location.href='/1_login';
})();
"""


def save_session_to_browser(access_token: str, refresh_token: str, remember: bool = True) -> None:
    """Persist tokens in browser cookies. Call only from login or restore flows."""
    max_age = _COOKIE_MAX_AGE if remember else 0
    js = _set_cookie_js("pv_at", access_token, max_age) + _set_cookie_js("pv_rt", refresh_token, max_age)
    stc.html(f"<script>{js}</script>", height=0)


def init_session() -> None:
    # Already authenticated — nothing to do (cookies already set at login/restore time)
    if st.session_state.get("user"):
        return

    # Phase 2: tokens arrived via query params from the JS cookie-read redirect
    at = st.query_params.get("pv_at", "")
    rt = st.query_params.get("pv_rt", "")
    if at and rt:
        st.query_params.clear()
        from services.auth_service import restore_session
        result = restore_session(at, rt)
        if result:
            st.session_state["user"] = result["user"]
            st.session_state["access_token"] = result["access_token"]
            st.session_state["refresh_token"] = result.get("refresh_token", rt)
            # Refresh the cookie with the (possibly rotated) tokens before rerunning
            save_session_to_browser(result["access_token"], result.get("refresh_token", rt))
            st.rerun()
            return
        # Tokens invalid — clear cookies
        stc.html(
            "<script>['pv_at','pv_rt'].forEach(n=>{document.cookie=n+'=;max-age=0;path=/'});</script>",
            height=0,
        )
        st.switch_page("pages/1_login.py")
        return

    # Phase 1: no session, no params — JS reads cookies and redirects with tokens
    stc.html(f"<script>{_JS_RESTORE}</script>", height=0)
    st.stop()


def require_auth() -> None:
    init_session()
    if not st.session_state.get("user"):
        st.switch_page("pages/1_login.py")


def logout() -> None:
    from services.auth_service import sign_out
    sign_out()
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    stc.html(f"<script>{_JS_LOGOUT}</script>", height=0)
    st.stop()
