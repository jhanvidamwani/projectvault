from __future__ import annotations
import streamlit as st
from services import ai_service as ai
from services import db_service as db


STARTER_PROMPTS = [
    "Summarize the project in 3 bullet points.",
    "What's the biggest risk right now?",
    "What should I focus on this week?",
    "What decisions were made recently?",
]


def render_ai_chat(project_id: str, project_title: str):
    chat_key = f"chat_{project_id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    messages: list[dict] = st.session_state[chat_key]

    st.markdown("### AI Project Assistant")
    st.caption("Ask anything about this project — grounded in your actual data.")

    # Starter prompts
    if not messages:
        for i in range(0, len(STARTER_PROMPTS), 2):
            col1, col2 = st.columns(2)
            for j, col in enumerate([col1, col2]):
                idx = i + j
                if idx < len(STARTER_PROMPTS):
                    prompt = STARTER_PROMPTS[idx]
                    with col:
                        if st.button(prompt[:22] + "…", key=f"starter_{idx}_{project_id}", use_container_width=True, help=prompt):
                            messages.append({"role": "user", "content": prompt})
                            st.session_state[chat_key] = messages
                            st.rerun()
        st.divider()

    # Chat history
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if user_input := st.chat_input("Ask about this project...", key=f"chat_input_{project_id}"):
        messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                context = db.get_project_full_state(project_id)
                context["snapshots"] = db.get_snapshots(project_id)[:5]
                response = ai.chat_with_project(messages, context)
            st.markdown(response)

        messages.append({"role": "assistant", "content": response})
        st.session_state[chat_key] = messages

    if messages and st.button("Clear chat", key=f"clear_chat_{project_id}"):
        st.session_state[chat_key] = []
        st.rerun()
