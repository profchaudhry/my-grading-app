import streamlit as st
from ui.styles import inject_global_css, render_sidebar_logo, render_sidebar_user
from typing import List


ROLE_ICONS  = {"admin": "🛡️", "faculty": "👨‍🏫", "faculty_ultra": "⭐", "student": "🎓"}
ROLE_COLORS = {"admin": "#92400e", "faculty": "#1e40af", "faculty_ultra": "#6d28d9", "student": "#166534"}
ROLE_BG     = {"admin": "#fef3c7", "faculty": "#dbeafe", "faculty_ultra": "#ede9fe",  "student": "#dcfce7"}

# ── Grouped menu for admin ────────────────────────────────────────
# Groups: {group_label: [items]}  — flat items have no group
ADMIN_GROUPS = {
    "📊 Dashboard":    None,          # top-level, no group
    "🎓 Academic Ops": [
        "🏛️ Departments",
        "📅 Semesters",
        "📚 Courses",
    ],
    "👥 User Control": [
        "👨‍🏫 Faculty",
        "🎓 Students",
        "✅ Pending Approvals",
        "📋 Enrollment",
        "📋 Bulk Enrollment",
    ],
    "📒 Gradebook":    None,
    "🏆 UPro Grade":   None,
    "📈 Reports":      None,
    "📣 Communications": None,
    "🔒 Change Password": None,
}


def base_console(title: str, menu_items: List[str]) -> str:
    """
    Renders the sidebar with branding, grouped navigation, and logout.
    Returns the currently selected menu item.
    """
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

    # ── Navigation label ──
    st.sidebar.markdown(
        '<div style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.45);'
        'text-transform:uppercase;letter-spacing:1.5px;padding:4px 16px 6px;">Navigation</div>',
        unsafe_allow_html=True,
    )

    # For admin, use grouped rendering
    if role == "admin":
        choice = _render_grouped_nav(menu_items)
    else:
        choice = st.sidebar.radio(
            "nav", menu_items,
            label_visibility="collapsed",
            key=f"nav_{role}",
        )

    # ── Logout button — styled via CSS, placed at the bottom ──
    st.sidebar.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
    st.sidebar.divider()
    st.sidebar.markdown("""
    <style>
    div[data-testid="stSidebar"] .logout-btn-wrap > button {
        background: rgba(255,255,255,0.12) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stSidebar"] .logout-btn-wrap > button:hover {
        background: rgba(255,80,80,0.30) !important;
        border-color: rgba(255,120,120,0.50) !important;
    }
    </style>
    <div class="logout-btn-wrap">
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        from services.auth_service import AuthService
        AuthService.logout()
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    return choice


def _render_grouped_nav(menu_items: List[str]) -> str:
    """Render grouped sidebar nav for admin with collapsible sections."""

    # Determine which items are in menu_items (in case subset passed)
    item_set = set(menu_items)

    # Build flat list preserving group membership
    groups: dict[str, list] = {}
    flat_items: list        = []

    for key, members in ADMIN_GROUPS.items():
        if members is None:
            # Top-level item
            if key in item_set:
                flat_items.append(("item", key))
        else:
            # Group — only include if any members present
            visible = [m for m in members if m in item_set]
            if visible:
                flat_items.append(("group", key, visible))

    # Initialise session state for expanded groups
    if "_sidebar_groups" not in st.session_state:
        st.session_state["_sidebar_groups"] = {}

    current = st.session_state.get(f"nav_{st.session_state.get('role','admin')}", menu_items[0])

    # Make sure current selection is valid
    if current not in item_set:
        current = menu_items[0]

    for entry in flat_items:
        if entry[0] == "item":
            label = entry[1]
            selected = current == label
            btn_style = "selected" if selected else ""
            st.sidebar.markdown(f"""
            <style>
            .nav-item-{_slugify(label)} > button {{
                background: {"rgba(255,255,255,0.18)" if selected else "transparent"} !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 8px !important;
                text-align: left !important;
                font-weight: {"600" if selected else "400"} !important;
                font-size: 0.88rem !important;
                padding: 0.42rem 0.75rem !important;
                margin-bottom: 2px !important;
            }}
            </style>
            <div class="nav-item-{_slugify(label)}">
            """, unsafe_allow_html=True)
            if st.sidebar.button(label, key=f"nav_item_{_slugify(label)}",
                                  use_container_width=True):
                st.session_state[f"nav_{st.session_state.get('role','admin')}"] = label
                st.rerun()
            st.sidebar.markdown("</div>", unsafe_allow_html=True)

        else:  # group
            _, group_label, members = entry
            group_key  = f"_grp_{_slugify(group_label)}"
            is_expanded = st.session_state["_sidebar_groups"].get(group_key, False)
            # Auto-expand if current item is in this group
            if current in members:
                is_expanded = True
                st.session_state["_sidebar_groups"][group_key] = True

            arrow = "▾" if is_expanded else "▸"
            st.sidebar.markdown(f"""
            <style>
            .nav-group-{_slugify(group_label)} > button {{
                background: transparent !important;
                color: rgba(255,255,255,0.70) !important;
                border: none !important;
                border-radius: 6px !important;
                text-align: left !important;
                font-weight: 700 !important;
                font-size: 0.76rem !important;
                text-transform: uppercase !important;
                letter-spacing: 0.08em !important;
                padding: 0.35rem 0.75rem !important;
                margin-top: 6px !important;
            }}
            .nav-group-{_slugify(group_label)} > button:hover {{
                background: rgba(255,255,255,0.08) !important;
                color: #ffffff !important;
            }}
            </style>
            <div class="nav-group-{_slugify(group_label)}">
            """, unsafe_allow_html=True)
            if st.sidebar.button(f"{arrow} {group_label}",
                                  key=f"grp_toggle_{_slugify(group_label)}",
                                  use_container_width=True):
                st.session_state["_sidebar_groups"][group_key] = not is_expanded
                st.rerun()
            st.sidebar.markdown("</div>", unsafe_allow_html=True)

            if is_expanded:
                for member in members:
                    selected = current == member
                    st.sidebar.markdown(f"""
                    <style>
                    .nav-child-{_slugify(member)} > button {{
                        background: {"rgba(255,255,255,0.16)" if selected else "rgba(255,255,255,0.04)"} !important;
                        color: #ffffff !important;
                        border: none !important;
                        border-left: {"3px solid rgba(255,255,255,0.7)" if selected else "3px solid transparent"} !important;
                        border-radius: 0 6px 6px 0 !important;
                        text-align: left !important;
                        font-weight: {"600" if selected else "400"} !important;
                        font-size: 0.86rem !important;
                        padding: 0.38rem 0.75rem 0.38rem 1.1rem !important;
                        margin-bottom: 2px !important;
                        margin-left: 8px !important;
                    }}
                    </style>
                    <div class="nav-child-{_slugify(member)}">
                    """, unsafe_allow_html=True)
                    if st.sidebar.button(member, key=f"nav_child_{_slugify(member)}",
                                          use_container_width=True):
                        st.session_state[f"nav_{st.session_state.get('role','admin')}"] = member
                        st.rerun()
                    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    return current


def _slugify(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "_", s.lower())
