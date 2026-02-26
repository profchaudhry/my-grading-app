import streamlit as st
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
    st.sidebar.markdown("""
        <div style="padding: 20px 16px 8px; border-bottom: 1px solid #2d3748; margin-bottom: 12px;">
            <div style="font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">
                🎓 SylemaX
            </div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                Academic Management System
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── User card ──
    st.sidebar.markdown(f"""
        <div style="
            margin: 8px 12px 16px;
            padding: 10px 14px;
            background: #2d3748;
            border-radius: 10px;
        ">
            <div style="font-size: 13px; font-weight: 600; color: #f1f5f9;">
                {icon} {display_name}
            </div>
            <div style="margin-top: 4px;">
                <span style="
                    font-size: 10px; font-weight: 700;
                    text-transform: uppercase; letter-spacing: 0.5px;
                    padding: 2px 8px; border-radius: 10px;
                    background: {bg}; color: {color};
                ">{role}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

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
        st.session_state.clear()
        st.rerun()

    return choice
