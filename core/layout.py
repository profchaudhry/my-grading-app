import streamlit as st
import re
from ui.styles import inject_global_css, render_sidebar_logo, render_sidebar_user
from typing import List


ROLE_ICONS  = {"admin": "🛡️", "faculty": "👨‍🏫", "faculty_ultra": "⭐", "student": "🎓"}

# ── Admin grouped menu definition ────────────────────────────────
# None = top-level item, list = collapsible group children
ADMIN_GROUPS = [
    ("item",  "📊 Dashboard"),
    ("group", "🎓 Academic Ops", ["🏛️ Departments", "📅 Semesters", "📚 Courses"]),
    ("group", "👥 User Control", ["👨‍🏫 Faculty", "🎓 Students", "✅ Pending Approvals",
                                   "📋 Enrollment", "📋 Bulk Enrollment"]),
    ("item",  "📒 Gradebook"),
    ("item",  "🏆 UPro Grade"),
    ("item",  "📈 Reports"),
    ("item",  "📣 Communications"),
    ("item",  "🔒 Change Password"),
]


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", s.lower())


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

    # ── Global sidebar button CSS ──────────────────────────────
    st.sidebar.markdown("""
    <style>
    /* All sidebar buttons — base reset */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        text-align: left !important;
        font-size: 0.88rem !important;
        font-weight: 400 !important;
        padding: 0.42rem 0.85rem !important;
        margin-bottom: 2px !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        box-shadow: none !important;
        transition: background 0.15s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.12) !important;
    }

    /* Selected nav item */
    section[data-testid="stSidebar"] .stButton > button[data-selected="true"],
    section[data-testid="stSidebar"] .nav-selected > .stButton > button {
        background: rgba(255,255,255,0.18) !important;
        font-weight: 600 !important;
        border-left: 3px solid rgba(255,255,255,0.85) !important;
    }

    /* Group header buttons */
    section[data-testid="stSidebar"] .nav-group-header > .stButton > button {
        color: rgba(255,255,255,0.55) !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.09em !important;
        margin-top: 8px !important;
        padding: 0.32rem 0.85rem !important;
    }
    section[data-testid="stSidebar"] .nav-group-header > .stButton > button:hover {
        color: #ffffff !important;
        background: rgba(255,255,255,0.07) !important;
    }

    /* Child items — indent */
    section[data-testid="stSidebar"] .nav-child > .stButton > button {
        padding-left: 1.4rem !important;
        font-size: 0.85rem !important;
        background: rgba(255,255,255,0.03) !important;
    }
    section[data-testid="stSidebar"] .nav-child > .stButton > button:hover {
        background: rgba(255,255,255,0.10) !important;
    }
    section[data-testid="stSidebar"] .nav-child-selected > .stButton > button {
        background: rgba(255,255,255,0.16) !important;
        font-weight: 600 !important;
        border-left: 3px solid rgba(255,255,255,0.80) !important;
        padding-left: calc(1.4rem - 3px) !important;
    }

    /* Logout button */
    section[data-testid="stSidebar"] .nav-logout > .stButton > button {
        background: rgba(255,255,255,0.10) !important;
        border: 1px solid rgba(255,255,255,0.22) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        justify-content: center !important;
        margin-top: 4px !important;
    }
    section[data-testid="stSidebar"] .nav-logout > .stButton > button:hover {
        background: rgba(220,60,60,0.28) !important;
        border-color: rgba(255,100,100,0.45) !important;
    }

    /* Nav section label */
    .nav-section-label {
        font-size: 10px;
        font-weight: 700;
        color: rgba(255,255,255,0.40);
        text-transform: uppercase;
        letter-spacing: 1.5px;
        padding: 4px 14px 6px;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.markdown('<div class="nav-section-label">Navigation</div>',
                        unsafe_allow_html=True)

    # ── Render nav ─────────────────────────────────────────────
    if role == "admin":
        choice = _render_admin_nav(menu_items)
    else:
        # Non-admin: simple flat radio (styled by global CSS from styles.py)
        choice = st.sidebar.radio(
            "nav", menu_items,
            label_visibility="collapsed",
            key=f"nav_{role}",
        )

    # ── Logout ─────────────────────────────────────────────────
    st.sidebar.divider()
    st.sidebar.markdown('<div class="nav-logout">', unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        from services.auth_service import AuthService
        AuthService.logout()
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    return choice


def _render_admin_nav(menu_items: List[str]) -> str:
    item_set = set(menu_items)
    nav_key  = "nav_admin"

    # Default to first valid item
    if nav_key not in st.session_state or st.session_state[nav_key] not in item_set:
        st.session_state[nav_key] = menu_items[0]

    current = st.session_state[nav_key]

    # Group expanded state
    if "_grp_state" not in st.session_state:
        st.session_state["_grp_state"] = {}

    for entry in ADMIN_GROUPS:
        if entry[0] == "item":
            label = entry[1]
            if label not in item_set:
                continue
            selected = current == label
            css_cls  = "nav-child-selected" if selected else "nav-child" if False else ""
            # Top-level items — use plain button
            st.sidebar.markdown(
                f'<div class="{"nav-child-selected" if selected else ""}">',
                unsafe_allow_html=True
            )
            if st.sidebar.button(label, key=f"nav_{_slugify(label)}",
                                  use_container_width=True):
                st.session_state[nav_key] = label
                st.rerun()
            st.sidebar.markdown('</div>', unsafe_allow_html=True)

        else:  # group
            _, group_label, members = entry
            visible = [m for m in members if m in item_set]
            if not visible:
                continue

            grp_key     = f"_grp_{_slugify(group_label)}"
            is_expanded = st.session_state["_grp_state"].get(grp_key, False)

            # Auto-expand if a child is selected
            if current in visible:
                is_expanded = True
                st.session_state["_grp_state"][grp_key] = True

            arrow = "▾" if is_expanded else "▸"
            st.sidebar.markdown('<div class="nav-group-header">',
                                unsafe_allow_html=True)
            if st.sidebar.button(f"{arrow}  {group_label}",
                                  key=f"grp_{_slugify(group_label)}",
                                  use_container_width=True):
                st.session_state["_grp_state"][grp_key] = not is_expanded
                st.rerun()
            st.sidebar.markdown('</div>', unsafe_allow_html=True)

            if is_expanded:
                for member in visible:
                    selected = current == member
                    st.sidebar.markdown(
                        f'<div class="{"nav-child-selected" if selected else "nav-child"}">',
                        unsafe_allow_html=True
                    )
                    if st.sidebar.button(member,
                                          key=f"nav_{_slugify(member)}",
                                          use_container_width=True):
                        st.session_state[nav_key] = member
                        st.rerun()
                    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    return current
