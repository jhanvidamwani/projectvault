from __future__ import annotations
import os
import hashlib
import streamlit as st
from services import db_service as db


def render_share_section(project: dict, can_edit: bool):
    share_token = project.get("share_token")
    app_url = os.getenv("APP_URL", "http://localhost:8501")
    share_url = f"{app_url}/shared/{share_token}"

    st.markdown("### Share this Project")
    st.text_input("Read-only share link", value=share_url, disabled=True, key="share_link_display")

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Anyone with this link can view the project in read-only mode.")

    if can_edit:
        st.divider()
        if st.checkbox("Password-protect share link", key="share_pw_toggle"):
            with st.form("share_password_form"):
                password = st.text_input("Set password (leave blank to remove)", type="password")
                save_pw = st.form_submit_button("Save Password Setting")
            if save_pw:
                if password:
                    hashed = hashlib.sha256(password.encode()).hexdigest()
                    db.update_project(project["id"], {"share_password_hash": hashed})
                    st.success("Share link is now password-protected.")
                else:
                    db.update_project(project["id"], {"share_password_hash": None})
                    st.success("Password protection removed.")
