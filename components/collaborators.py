from __future__ import annotations
import streamlit as st
from services import db_service as db


ROLE_LABELS = {"owner": "Owner", "editor": "Editor", "viewer": "Viewer"}


def render_collaborators(project_id: str, current_user_id: str, can_edit: bool):
    st.markdown("### Team Members")

    collaborators = db.get_collaborators(project_id)
    for c in collaborators:
        u = c.get("users") or {}
        name = u.get("name") or u.get("email") or "Unknown"
        role = c.get("role", "viewer")
        col_name, col_role, col_action = st.columns([4, 2, 1])
        col_name.markdown(f"**{name}**")
        col_role.markdown(ROLE_LABELS.get(role, role))
        if can_edit and role != "owner" and c.get("user_id") != current_user_id:
            with col_action:
                if st.button("Remove", key=f"remove_collab_{c['id']}", use_container_width=True):
                    from services.auth_service import get_supabase_admin
                    get_supabase_admin().table("collaborators").delete().eq("id", c["id"]).execute()
                    st.rerun()

    if can_edit:
        st.divider()
        st.markdown("#### Invite Collaborator")
        with st.form("invite_form"):
            invite_email = st.text_input("Email address", placeholder="colleague@example.com")
            invite_role = st.selectbox("Role", ["editor", "viewer"], format_func=lambda x: ROLE_LABELS[x])
            send_invite = st.form_submit_button("Send Invite", type="primary")

        if send_invite:
            if not invite_email.strip():
                st.error("Email is required.")
            else:
                user = db.get_user_by_email(invite_email.strip().lower())
                if not user:
                    st.warning(f"No account found for {invite_email}. They need to sign up first.")
                elif user["id"] == current_user_id:
                    st.error("You can't invite yourself.")
                else:
                    existing_role = db.get_user_role(project_id, user["id"])
                    if existing_role:
                        st.warning(f"{invite_email} is already a {existing_role}.")
                    else:
                        db.add_collaborator(project_id, user["id"], invite_role, current_user_id)
                        st.success(f"Added {invite_email} as {invite_role}.")
                        st.rerun()
