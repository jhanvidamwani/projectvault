import streamlit as st
from utils.formatting import health_color_class, health_icon


def render_health_score(score: int, explanation: str = ""):
    css_cls = health_color_class(score)
    icon = health_icon(score)
    st.markdown(f"""
    <div class="pv-card" style="text-align:center;">
        <div class="{css_cls}" style="font-size:2rem; font-weight:800;">{icon} {score}<span style="font-size:1rem">/100</span></div>
        <div style="font-size:0.8rem; color:#999999; margin-top:0.4rem;">AI Health Score</div>
        {f'<div style="margin-top:0.6rem; color:#333333; font-size:0.85rem; font-style:italic;">{explanation}</div>' if explanation else ''}
    </div>
    """, unsafe_allow_html=True)
