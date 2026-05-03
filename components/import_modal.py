from __future__ import annotations
import os
import html as _html
import streamlit as st
import streamlit.components.v1 as stc
from services import import_service

# ── Drop zone CSS injected once ───────────────────────────────────────────────
_DROPZONE_CSS = """
<style>
/* Fix uploadUpload duplicate text in browse button */
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] > div > p:first-of-type,
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] > div > span:first-of-type {
    display: none !important;
}
/* Make the button font-size 0 to nuke the icon glyph, restore on the label p */
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] {
    font-size:     0 !important;
    background:    #FFF5F0 !important;
    border:        1px solid rgba(224,112,96,0.35) !important;
    border-radius: 8px !important;
    color:         #6B4A3E !important;
    font-weight:   500 !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] > div > p {
    font-size:  0.82rem !important;
    color:      #6B4A3E !important;
    display:    block !important;
    margin:     0 !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]:hover {
    background:   #FFE4D8 !important;
    border-color: #E07060 !important;
}
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed rgba(224,112,96,0.4) !important;
    border-radius: 12px !important;
    background: #FFF5F0 !important;
    min-height: 130px !important;
    cursor: pointer !important;
    transition: border-color 0.2s ease, background 0.2s ease !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #E07060 !important;
    background: #FFE4D8 !important;
    box-shadow: none !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div:first-child svg {
    color: #E07060 !important;
    width: 28px !important;
    height: 28px !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span {
    color: #6B4A3E !important;
    font-size: 0.85rem !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] small {
    color: #A88F87 !important;
    font-size: 0.75rem !important;
}
[data-testid="stFileUploaderDropzone"].pv-drag-over {
    border-color: #E07060 !important;
    background: #FFE4D8 !important;
    box-shadow: 0 0 0 3px rgba(224,112,96,0.12) !important;
}
[data-testid="stFileUploaderDropzone"].pv-drop-success {
    border-color: #8E5E4E !important;
    background: rgba(142,94,78,0.05) !important;
    box-shadow: none !important;
}
</style>
"""

# ── Drag-over JS animation (injected via component) ───────────────────────────
_DROPZONE_JS = """
<script>
(function poll() {
  const zone = window.parent.document.querySelector('[data-testid="stFileUploaderDropzone"]');
  if (!zone) { setTimeout(poll, 300); return; }

  zone.addEventListener('dragenter', () => zone.classList.add('pv-drag-over'));
  zone.addEventListener('dragover',  (e) => { e.preventDefault(); zone.classList.add('pv-drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('pv-drag-over'));
  zone.addEventListener('drop', () => {
    zone.classList.remove('pv-drag-over');
    zone.classList.add('pv-drop-success');
    setTimeout(() => zone.classList.remove('pv-drop-success'), 2000);
  });
})();
</script>
"""

# ── Clipboard JS (reads clipboard, reloads page with query param) ─────────────
_CLIPBOARD_JS = """
<button onclick="readClipboard()" style="
  background:#FFF5F0; color:#6B4A3E; border:1px solid rgba(224,112,96,0.35);
  border-radius:8px; padding:6px 16px; font-size:0.82rem;
  cursor:pointer; display:inline-flex; align-items:center; gap:6px;
  font-family:system-ui,sans-serif; transition:background 0.2s;
" onmouseover="this.style.background='#FFE4D8'" onmouseout="this.style.background='#FFF5F0'">
  Paste from Clipboard
</button>
<script>
async function readClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (!text || !text.trim()) { alert('Clipboard is empty or has no text.'); return; }
    const url = new URL(window.parent.location.href);
    url.searchParams.set('imp_clipboard', text.substring(0, 5000));
    window.parent.location.href = url.toString();
  } catch(e) {
    alert('Clipboard access denied by your browser.\\nPlease switch to the Paste Text / URL tab and paste manually (Cmd+V).');
  }
}
</script>
"""


# ── Shared: Import Preview ────────────────────────────────────────────────────

def _render_preview(analysis: dict) -> dict:
    st.markdown("#### Import Preview")
    st.caption("AI extracted the following — edit anything before confirming.")

    col_fields, col_score = st.columns([3, 1])
    with col_fields:
        analysis["project_name"] = st.text_input(
            "Project Name", value=analysis.get("project_name", ""), key="imp_name"
        )
        analysis["description"] = st.text_area(
            "Description", value=analysis.get("description", ""), height=80, key="imp_desc"
        )
        tags_str = st.text_input(
            "Tags (comma-separated)", value=", ".join(analysis.get("tags", [])), key="imp_tags"
        )
        analysis["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

    with col_score:
        score = analysis.get("health_score", 60)
        color = "#8E5E4E" if score >= 70 else "#C4A882" if score >= 40 else "#CF6F61"
        st.markdown(
            f'<div style="text-align:center;padding:1rem 0.5rem;background:#FFF5F0;border:1px solid rgba(142,94,78,0.18);border-radius:12px;margin-top:1.6rem;">'
            f'<div style="font-size:2.2rem;font-weight:800;color:{color};">{score}</div>'
            f'<div style="color:#A88F87;font-size:0.72rem;margin-top:2px;">AI Health</div>'
            f'<div style="color:#7A6560;font-size:0.7rem;margin-top:4px;padding:0 4px;">{_html.escape(str(analysis.get("health_explanation",""))[:80])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if analysis.get("import_narrative"):
        st.info(f"**AI Summary:** {analysis['import_narrative']}")

    col_m, col_t = st.columns(2)
    with col_m:
        milestones = analysis.get("milestones", [])
        if milestones:
            st.markdown("**Detected Milestones**")
            for m in milestones[:6]:
                status_icon = "done" if m.get("status") == "completed" else "pending"
                st.markdown(f"- [{status_icon}] {m.get('title','')} `{m.get('date','?')}`")

    with col_t:
        tools = analysis.get("detected_tools", [])
        if tools:
            st.markdown("**Auto-linked Workspaces**")
            from services import links_service
            for t in tools:
                preset = links_service.PLATFORM_PRESETS.get(t, {})
                st.markdown(f"- {preset.get('label', t)}")

    return analysis


# ── Tab 1: File Upload ────────────────────────────────────────────────────────

_TYPE_ICON: dict[str, str] = {}


def _render_file_tab() -> None:
    # Inject drop zone CSS
    st.markdown(_DROPZONE_CSS, unsafe_allow_html=True)

    # Clipboard button
    col_clip, col_hint = st.columns([1, 4])
    with col_clip:
        stc.html(_CLIPBOARD_JS, height=38)
    with col_hint:
        st.caption("Copies clipboard text → switches to Paste tab automatically")

    st.write("")

    # Styled native uploader (drag-and-drop already built in; CSS makes it beautiful)
    uploaded = st.file_uploader(
        "Drag & drop files here, or click to browse",
        type=["pdf", "docx", "txt", "md", "csv", "pptx", "xlsx", "zip",
              "py", "js", "ts", "json", "yaml", "yml"],
        accept_multiple_files=True,
        key="imp_file_upload",
        label_visibility="visible",
    )

    # Inject drag-over animation JS after the uploader is rendered
    stc.html(_DROPZONE_JS, height=0)

    if not uploaded:
        st.caption("Supports PDF · DOCX · TXT · MD · CSV · XLSX · PPTX · ZIP · and code files")
        return

    # ── File list with status icons ───────────────────────────────────────────
    st.markdown("**Selected files:**")
    for f in uploaded:
        ext = f.name.lower().rsplit(".", 1)[-1] if "." in f.name else ""
        icon = _TYPE_ICON.get(ext, "")
        size_kb = len(f.getvalue()) / 1024
        size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        st.markdown(
            f"<div style='font-size:0.85rem; color:#A88F87; margin:2px 0;'>"
            f"<b style='color:#2C1810'>{f.name}</b> "
            f"<span style='color:#7A6560'>({size_str})</span></div>",
            unsafe_allow_html=True,
        )

    st.write("")
    if not st.button("Analyze Files", type="primary", key="imp_analyze_files"):
        return

    # ── Processing with step-by-step progress ────────────────────────────────
    with st.status("Processing your files...", expanded=True) as status:
        combined_parts: list[str] = []
        is_code_project = False
        zip_summaries: list[str] = []

        zips = [f for f in uploaded if f.name.lower().endswith(".zip")]
        regular = [f for f in uploaded if not f.name.lower().endswith(".zip")]

        # Handle ZIPs
        for zf in zips:
            st.write(f"Unpacking {zf.name}...")
            result = import_service.extract_text_from_zip(zf.getvalue())

            if result.get("error") == "password_protected":
                st.error(f"{zf.name} is password-protected — please extract it first.")
                continue
            if result.get("error") == "corrupted":
                st.error(f"{zf.name} appears corrupted and could not be opened.")
                continue

            # Show ZIP file tree
            st.markdown(f"**{zf.name}** — {result['summary']}")
            tree_lines = []
            for fname, size_kb, s in result["file_tree"][:20]:
                ext = fname.lower().rsplit(".", 1)[-1] if "." in fname else ""
                icon = _TYPE_ICON.get(ext, "")
                if s == "ok":
                    tree_lines.append(f"{fname} ({size_kb:.0f} KB)")
                elif s == "skipped":
                    tree_lines.append(f"{fname} <span style='color:#7A6560'>(skipped — unsupported)</span>")
                elif s == "empty":
                    tree_lines.append(f"{fname} (no text extracted)")

            st.markdown(
                "<div style='font-size:0.8rem;color:#6B4A3E;background:#FFF5F0;border:1px solid rgba(142,94,78,0.15);"
                "border-radius:8px;padding:10px 14px;margin:6px 0;line-height:1.8;'>"
                + "<br>".join(tree_lines[:20])
                + ("..." if len(result["file_tree"]) > 20 else "")
                + "</div>",
                unsafe_allow_html=True,
            )

            if result["combined_text"].strip():
                combined_parts.append(result["combined_text"])
            if result["is_code_project"]:
                is_code_project = True
            zip_summaries.append(result["summary"])

        # Handle regular files
        if regular:
            st.write(f"Reading {len(regular)} file(s)...")
            prog = st.progress(0)
            for i, f in enumerate(regular):
                text = import_service.extract_text(f.getvalue(), f.name)
                if text.strip():
                    ext = f.name.lower().rsplit(".", 1)[-1] if "." in f.name else ""
                    if ext in import_service._CODE_EXTS:
                        is_code_project = True
                    combined_parts.append(f"=== {f.name} ===\n{text[:4000]}")
                prog.progress((i + 1) / len(regular))

        if not combined_parts:
            status.update(label="No readable text found.", state="error")
            st.error("Could not extract readable text from the uploaded files.")
            return

        all_text = "\n\n".join(combined_parts)

        # Truncation warning
        MAX_CHARS = 100_000
        truncated = len(all_text) > MAX_CHARS
        if truncated:
            all_text = all_text[:MAX_CHARS]
            st.warning("Large project detected — analyzing first 100 KB of content.")

        # Append code project hint for AI analysis
        if is_code_project:
            all_text += "\n\n[NOTE: This appears to be a code/engineering project based on the file types detected.]"

        st.write("Analyzing with AI...")
        analysis = import_service.analyze_content(all_text)

        # Auto-add "engineering" tag for code projects
        if is_code_project and "engineering" not in [t.lower() for t in analysis.get("tags", [])]:
            analysis["tags"] = analysis.get("tags", []) + ["engineering"]

        project_name = analysis.get("project_name", "Unknown")
        status.update(label=f"Done! Detected project: \"{project_name}\"", state="complete")

    st.session_state["import_analysis"] = analysis
    st.session_state["import_raw_text"] = all_text
    st.session_state["import_linked_urls"] = []
    st.rerun()


# ── Tab 2: Google Drive ───────────────────────────────────────────────────────

def _build_gdrive_flow(client_id: str, client_secret: str, redirect_uri: str):
    from google_auth_oauthlib.flow import Flow
    return Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        redirect_uri=redirect_uri,
    )


def _list_drive_files(token: str) -> list[dict]:
    try:
        import requests
        resp = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "pageSize": 30,
                "orderBy": "modifiedTime desc",
                "q": "mimeType!='application/vnd.google-apps.folder' and trashed=false",
                "fields": "files(id,name,mimeType,webViewLink)",
            },
            timeout=10,
        )
        return resp.json().get("files", [])
    except Exception:
        return []


def _fetch_drive_file_text(token: str, file_id: str) -> str:
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}"}
        # Export Google Workspace files as plain text
        export = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
            headers=headers, params={"mimeType": "text/plain"}, timeout=15,
        )
        if export.status_code == 200:
            return export.text[:6000]
        # Fallback: download binary (for uploaded non-Workspace files)
        dl = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            headers=headers, timeout=15,
        )
        if dl.status_code == 200:
            return dl.text[:6000]
    except Exception:
        pass
    return ""


def _render_gdrive_tab() -> None:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    app_url = os.getenv("APP_URL", "http://localhost:8501")
    redirect_uri = f"{app_url}/2_dashboard"

    if not client_id or not client_secret:
        st.info("Google Drive import requires a Google Cloud project with Drive API enabled.")
        if st.checkbox("Show setup instructions", key="gdrive_setup_toggle"):
            st.markdown(
                '<div style="background:#FFF5F0;border:1px solid rgba(142,94,78,0.18);border-radius:12px;padding:1rem 1.25rem;font-size:0.82rem;color:#6B4A3E;line-height:1.8;">'
                '<b style="color:#2C1810;">1.</b> Go to Google Cloud Console → create or select a project<br>'
                '<b style="color:#2C1810;">2.</b> APIs &amp; Services → Enable APIs → enable <b>Google Drive API</b><br>'
                '<b style="color:#2C1810;">3.</b> OAuth consent screen → External, add your email as test user<br>'
                '<b style="color:#2C1810;">4.</b> Credentials → Create OAuth 2.0 Client ID (Web app)<br>'
                '&nbsp;&nbsp;&nbsp;&nbsp;Redirect URI: <code>http://localhost:8501/2_dashboard</code><br>'
                '<b style="color:#2C1810;">5.</b> Add to <code>.env</code>: <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code><br>'
                '<b style="color:#2C1810;">6.</b> Restart the app'
                '</div>',
                unsafe_allow_html=True,
            )
        return

    # Already connected
    if st.session_state.get("gdrive_token"):
        st.success("Google Drive connected")
        if st.button("Disconnect Drive", key="gdrive_disconnect"):
            st.session_state.pop("gdrive_token", None)
            st.rerun()

        with st.spinner("Loading your recent Drive files..."):
            files = _list_drive_files(st.session_state["gdrive_token"])

        if not files:
            st.warning("No files found in your Drive, or token has expired.")
            return

        file_map = {f["id"]: f for f in files}
        selected_ids = st.multiselect(
            "Select files to import",
            list(file_map.keys()),
            format_func=lambda fid: file_map[fid]["name"],
            key="gdrive_selected",
        )

        if selected_ids and st.button("Import Selected Files", type="primary", key="gdrive_import_btn"):
            combined_parts, linked_urls = [], []
            for fid in selected_ids:
                fname = file_map[fid]["name"]
                with st.spinner(f"Fetching {fname}..."):
                    text = _fetch_drive_file_text(st.session_state["gdrive_token"], fid)
                if text.strip():
                    combined_parts.append(f"=== {fname} ===\n{text}")
                linked_urls.append({
                    "platform": "googledocs",
                    "label": fname,
                    "url": file_map[fid].get("webViewLink", f"https://drive.google.com/file/d/{fid}"),
                    "icon": "",
                })

            all_text = "\n\n".join(combined_parts)
            if not all_text.strip():
                st.error("Could not extract text from selected files.")
                return

            with st.spinner("AI is analyzing your files..."):
                analysis = import_service.analyze_content(all_text)

            st.session_state["import_analysis"] = analysis
            st.session_state["import_raw_text"] = all_text
            st.session_state["import_linked_urls"] = linked_urls
            st.rerun()
        return

    # Not connected — show auth button
    try:
        flow = _build_gdrive_flow(client_id, client_secret, redirect_uri)
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state="gdrive_import",
        )
        st.markdown("Connect your Google Drive to pick Docs, Sheets, or Slides to import.")
        st.link_button("Connect Google Drive", auth_url, use_container_width=False)
    except ImportError:
        st.error("Missing package. Run: `python3 -m pip install google-auth-oauthlib`")


# ── Tab 3: Paste Text / URL ───────────────────────────────────────────────────

def _render_paste_tab() -> None:
    url_input = st.text_input(
        "Public URL (optional)",
        placeholder="https://notion.so/my-project-brief...",
        key="imp_url",
    )
    text_input = st.text_area(
        "Paste project content",
        placeholder="Paste your PRD, project brief, meeting notes, or any project text here...",
        height=220,
        key="imp_paste_text",
    )

    if st.button("Analyze Content", type="primary", key="imp_analyze_paste"):
        raw_parts = []
        linked_urls = []

        if url_input.strip().startswith("http"):
            with st.spinner(f"Fetching {url_input.strip()}..."):
                fetched = import_service.fetch_url_content(url_input.strip())
            if fetched and not fetched.startswith("Could not fetch"):
                raw_parts.append(f"=== Content from {url_input.strip()} ===\n{fetched}")
                linked_urls.append(import_service.url_to_link_dict(url_input.strip()))
            else:
                st.warning(f"Could not fetch URL — continuing with pasted text only.")

        if text_input.strip():
            raw_parts.append(text_input.strip())

        if not raw_parts:
            st.error("Please paste some content or provide a valid URL.")
            return

        all_text = "\n\n".join(raw_parts)
        with st.spinner("AI is analyzing your project..."):
            analysis = import_service.analyze_content(all_text)

        st.session_state["import_analysis"] = analysis
        st.session_state["import_raw_text"] = all_text
        st.session_state["import_linked_urls"] = linked_urls
        st.rerun()


# ── Tab 4: GitHub Repo ────────────────────────────────────────────────────────

def _render_github_tab() -> None:
    st.markdown(
        '<p style="color:#6B4A3E;font-size:0.85rem;margin-bottom:0.75rem;">'
        'Paste a public GitHub repo URL — ProjectVault will download it, extract README + code files, '
        'and auto-detect tags, milestones, and a description.'
        '</p>',
        unsafe_allow_html=True,
    )
    st.caption("Private repos need a GitHub token — add one in Settings.")

    repo_url = st.text_input(
        "GitHub repo URL",
        placeholder="https://github.com/owner/repo  (or just owner/repo)",
        key="imp_github_url",
    )
    branch = st.text_input(
        "Branch (optional)",
        placeholder="leave empty for default branch",
        key="imp_github_branch",
    )

    if not st.button("Import Repo", type="primary", key="imp_github_btn"):
        return

    if not repo_url.strip():
        st.error("Enter a GitHub repo URL.")
        return

    from services import github_service

    with st.status("Connecting to GitHub...", expanded=True) as status:
        st.write(f"Fetching `{repo_url.strip()}` …")
        result = github_service.fetch_repo_zip(repo_url.strip(), branch.strip())

        if result.get("error"):
            status.update(label="Import failed", state="error")
            st.error(result["error"])
            return

        st.write(f"Downloaded `{result['repo_path']}` (branch: `{result['branch']}`)")
        st.write("Extracting files from archive…")
        zip_result = import_service.extract_text_from_zip(result["bytes"])

        if zip_result.get("error"):
            status.update(label="Extract failed", state="error")
            st.error(f"Could not read repo: {zip_result['error']}")
            return

        st.write(zip_result["summary"])

        # Show file tree preview
        tree_lines = []
        for fname, size_kb, s in zip_result["file_tree"][:25]:
            if s == "ok":
                tree_lines.append(f"{fname} ({size_kb:.0f} KB)")
            elif s == "skipped":
                tree_lines.append(f"{fname} (skipped)")
        if tree_lines:
            st.markdown(
                "<div style='font-size:0.78rem;color:#6B4A3E;background:#FFF5F0;border:1px solid rgba(142,94,78,0.15);"
                "border-radius:8px;padding:10px 14px;margin:6px 0;line-height:1.7;'>"
                + "<br>".join(tree_lines)
                + ("..." if len(zip_result["file_tree"]) > 25 else "")
                + "</div>",
                unsafe_allow_html=True,
            )

        all_text = zip_result["combined_text"]
        if not all_text.strip():
            status.update(label="No readable content", state="error")
            st.error("This repo had no readable text files (might be all binaries).")
            return

        # Truncate large repos
        MAX_CHARS = 100_000
        if len(all_text) > MAX_CHARS:
            all_text = all_text[:MAX_CHARS]
            st.warning("Large repo — analyzing first 100 KB.")

        if zip_result["is_code_project"]:
            all_text += "\n\n[NOTE: This is a code/engineering project (GitHub repository).]"

        st.write("Running AI analysis…")
        analysis = import_service.analyze_content(all_text)

        # Always tag as engineering + add github linked URL
        if "engineering" not in [t.lower() for t in analysis.get("tags", [])]:
            analysis["tags"] = analysis.get("tags", []) + ["engineering"]

        # Use repo name as project name if AI didn't extract one
        if not analysis.get("project_name"):
            analysis["project_name"] = result["repo_path"].split("/")[-1]

        project_name = analysis.get("project_name", "Unknown")
        status.update(label=f"Imported: \"{project_name}\"", state="complete")

    # Auto-link the GitHub repo
    repo_link = {
        "platform": "github",
        "label":    result["repo_path"],
        "url":      f"https://github.com/{result['repo_path']}",
        "icon":     "",
    }

    st.session_state["import_analysis"]    = analysis
    st.session_state["import_raw_text"]    = all_text
    st.session_state["import_linked_urls"] = [repo_link]
    st.rerun()


# ── Main entry point ──────────────────────────────────────────────────────────

def render_import_modal(user: dict) -> None:
    # Handle clipboard query param (set by the JS clipboard button)
    _clipboard = st.query_params.get("imp_clipboard", "")
    if _clipboard:
        st.session_state["imp_paste_prefill"] = _clipboard
        st.session_state["show_import_modal"] = True
        st.query_params.clear()
        st.info("Clipboard text captured — switch to the **Paste Text / URL** tab to use it.")

    st.caption("Upload files, paste a GitHub repo, connect Google Drive, or paste your brief — AI auto-analyzes everything.")

    tab_files, tab_github, tab_drive, tab_paste = st.tabs(
        ["Upload Files", "GitHub Repo", "Google Drive", "Paste Text / URL"]
    )

    with tab_files:
        _render_file_tab()

    with tab_github:
        _render_github_tab()

    with tab_drive:
        _render_gdrive_tab()

    with tab_paste:
        _render_paste_tab()

    # ── Shared preview + confirm ──────────────────────────────────────────────
    if "import_analysis" in st.session_state:
        st.divider()
        analysis = _render_preview(st.session_state["import_analysis"])
        st.session_state["import_analysis"] = analysis  # persist edits

        col_confirm, col_cancel, _ = st.columns([2, 2, 3])
        with col_confirm:
            if st.button("Confirm Import", type="primary", use_container_width=True, key="imp_confirm"):
                if not analysis.get("project_name", "").strip():
                    st.error("Project name cannot be empty.")
                    return
                with st.spinner("Creating project, snapshot, and embeddings..."):
                    project = import_service.create_project_from_import(
                        user_id=user["id"],
                        analysis=analysis,
                        raw_text=st.session_state.get("import_raw_text", ""),
                        linked_urls=st.session_state.get("import_linked_urls", []),
                    )
                for key in ["import_analysis", "import_raw_text", "import_linked_urls"]:
                    st.session_state.pop(key, None)
                st.session_state["show_import_modal"] = False
                st.session_state["current_project"] = project["id"]
                st.success(f"Project '{project['title']}' imported!")
                st.switch_page("pages/3_project.py")

        with col_cancel:
            if st.button("Start Over", use_container_width=True, key="imp_cancel"):
                for key in ["import_analysis", "import_raw_text", "import_linked_urls"]:
                    st.session_state.pop(key, None)
                st.rerun()
