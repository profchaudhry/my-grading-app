import streamlit as st
from ui.styles import inject_global_css, render_sidebar_logo, render_sidebar_user, section_header
from typing import List


ROLE_ICONS = {
    "admin": "🛡️",
    "faculty": "👨‍🏫",
    "student": "🎓",
}

ROLE_COLORS = {
    "admin":   "#92400e",
    "faculty": "#1e40af",
    "student": "#166534",
}

ROLE_BG = {
    "admin":   "#fef3c7",
    "faculty": "#dbeafe",
    "student": "#dcfce7",
}


def base_console(title: str, menu_items: List[str]) -> str:
    """
    Renders a professional sidebar with branding, role badge,
    navigation menu, and logout button.
    Returns the currently selected menu item.
    """
    inject_global_css()
    role = st.session_state.get("role", "")
    user = st.session_state.get("user")
    profile = st.session_state.get("profile", {}) or {}

    icon = ROLE_ICONS.get(role, "👤")
    color = ROLE_COLORS.get(role, "#475569")
    bg = ROLE_BG.get(role, "#f1f5f9")

    role_val = st.session_state.get("role", "")
    # Students use full_name; faculty/admin use first+last
    if role_val == "student" and profile.get("full_name","").strip():
        display_name = profile["full_name"].strip()
    else:
        first = profile.get("first_name", "").strip()
        last  = profile.get("last_name",  "").strip()
        display_name = f"{first} {last}".strip() or (user.email if user else "User")

    # ── Branding ──
    render_sidebar_logo()

    render_sidebar_user(display_name, role)

    # ── Navigation ──
    st.sidebar.markdown(
        '<div style="font-size: 10px; font-weight: 700; color: #64748b; '
        'text-transform: uppercase; letter-spacing: 1px; padding: 0 16px 6px;">Navigation</div>',
        unsafe_allow_html=True
    )

    choice = st.sidebar.radio(
        "nav",
        menu_items,
        label_visibility="collapsed",
        key=f"nav_{role}"
    )

    st.sidebar.divider()

    # ── Logout ──
    if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        from services.auth_service import AuthService
        AuthService.logout()
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()
        st.rerun()

    return choice
