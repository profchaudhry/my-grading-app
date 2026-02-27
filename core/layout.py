import streamlit as st
from ui.styles import inject_global_css, render_sidebar_logo, render_sidebar_user
from typing import List


def base_console(title: str, menu_items: List[str]) -> str:
    inject_global_css()

    role    = st.session_state.get("role", "")
    user    = st.session_state.get("user")
    profile = st.session_state.get("profile", {}) or {}

    # Display name
    if role == "student" and profile.get("full_name", "").strip():
        display_name = profile["full_name"].strip()
    else:
        first = profile.get("first_name", "").strip()
        last  = profile.get("last_name",  "").strip()
        display_name = f"{first} {last}".strip() or (user.email if user else "User")

    render_sidebar_logo()
    render_sidebar_user(display_name, role)

    st.sidebar.markdown("""
    <style>
    .nav-section-lbl {
        font-size: 9px; font-weight: 800;
        color: rgba(255,255,255,0.38);
        text-transform: uppercase; letter-spacing: 1.6px;
        padding: 10px 6px 2px 6px; margin: 0; display: block;
    }
    section[data-testid="stSidebar"] .logout-wrap button {
        background-color: rgba(255,255,255,0.13) !important;
        color: #ffffff !important;
        border: 1.5px solid rgba(255,255,255,0.30) !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        box-shadow: none !important;
        background-image: none !important;
    }
    section[data-testid="stSidebar"] .logout-wrap button:hover {
        background-color: rgba(200,40,40,0.32) !important;
        border-color: rgba(255,80,80,0.50) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.markdown('<span class="nav-section-lbl">Navigation</span>',
                        unsafe_allow_html=True)

    choice = st.sidebar.radio(
        "nav", menu_items,
        label_visibility="collapsed",
        key=f"nav_{role}",
    )

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown('<div class="logout-wrap">', unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        from services.auth_service import AuthService
        AuthService.logout()
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    return choice
