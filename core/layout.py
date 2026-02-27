import streamlit as st
import re
from ui.styles import inject_global_css, render_sidebar_logo, render_sidebar_user
from typing import List


ROLE_ICONS = {"admin": "🛡️", "faculty": "👨‍🏫", "faculty_ultra": "⭐", "student": "🎓"}


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", s.lower())


# ── Admin grouped menu ─────────────────────────────────────────────
# Each entry: ("item", label) | ("group", label, [children])
ADMIN_GROUPS = [
    ("item",  "📊 Dashboard"),
    ("group", "🎓 Academic Ops", [
        "🏛️ Departments", "📅 Semesters", "📚 Courses"
    ]),
    ("group", "👥 User Control", [
        "👨‍🏫 Faculty", "🎓 Students", "✅ Pending Approvals",
        "📋 Enrollment", "📋 Bulk Enrollment",
    ]),
    ("item",  "📒 Gradebook"),
    ("item",  "🏆 UPro Grade"),
    ("item",  "📈 Reports"),
    ("item",  "📣 Communications"),
    ("item",  "🔒 Change Password"),
]


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

    # ── Nav label ─────────────────────────────────────────────────
    st.sidebar.markdown(
        '<p style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.45);'
        'text-transform:uppercase;letter-spacing:1.5px;margin:4px 0 6px 4px;">Navigation</p>',
        unsafe_allow_html=True,
    )

    # ── Navigation ────────────────────────────────────────────────
    if role == "admin":
        choice = _render_admin_nav(menu_items)
    else:
        choice = st.sidebar.radio(
            "nav", menu_items,
            label_visibility="collapsed",
            key=f"nav_{role}",
        )

    # ── Logout ────────────────────────────────────────────────────
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.divider()
    st.sidebar.markdown("""
    <style>
    /* Logout button */
    section[data-testid="stSidebar"] button[kind="secondary"]:last-of-type,
    div[data-testid="stSidebarContent"] > div > div > div:last-child .stButton > button {
        background: rgba(255,255,255,0.12) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        font-weight: 500 !important;
    }
    div[data-testid="stSidebarContent"] > div > div > div:last-child .stButton > button:hover {
        background: rgba(220,50,50,0.30) !important;
        border-color: rgba(255,100,100,0.50) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        from services.auth_service import AuthService
        AuthService.logout()
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

    return choice


def _render_admin_nav(menu_items: List[str]) -> str:
    """
    Renders admin navigation using st.sidebar.radio for each group/section
    so labels always show correctly. Groups are collapsible via session state.
    """
    item_set = set(menu_items)
    nav_key  = "nav_admin_choice"

    if nav_key not in st.session_state or st.session_state[nav_key] not in item_set:
        st.session_state[nav_key] = menu_items[0]

    current = st.session_state[nav_key]

    if "_grp_state" not in st.session_state:
        st.session_state["_grp_state"] = {}

    # Collect top-level items and groups separately
    for entry in ADMIN_GROUPS:
        if entry[0] == "item":
            label = entry[1]
            if label not in item_set:
                continue
            _nav_radio_item(label, current, nav_key)

        else:
            _, group_label, children = entry
            visible = [c for c in children if c in item_set]
            if not visible:
                continue

            grp_key     = f"_grp_{_slugify(group_label)}"
            is_expanded = st.session_state["_grp_state"].get(grp_key, False)

            # Auto-expand if active child is in this group
            if current in visible:
                is_expanded = True
                st.session_state["_grp_state"][grp_key] = True

            # Group header — styled markdown button simulation
            arrow = "▾" if is_expanded else "▸"
            st.sidebar.markdown(f"""
            <style>
            #grp_btn_{_slugify(group_label)} + div .stButton > button {{
                background: transparent !important;
                color: rgba(255,255,255,0.55) !important;
                border: none !important;
                font-size: 0.73rem !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.09em !important;
                padding: 0.28rem 0.6rem !important;
                box-shadow: none !important;
                text-align: left !important;
                justify-content: flex-start !important;
            }}
            #grp_btn_{_slugify(group_label)} + div .stButton > button:hover {{
                color: #ffffff !important;
                background: rgba(255,255,255,0.06) !important;
            }}
            </style>
            <span id="grp_btn_{_slugify(group_label)}"></span>
            """, unsafe_allow_html=True)

            if st.sidebar.button(f"{arrow}  {group_label}",
                                  key=f"grp_{_slugify(group_label)}",
                                  use_container_width=True):
                st.session_state["_grp_state"][grp_key] = not is_expanded
                st.rerun()

            if is_expanded:
                # Render children as a radio group
                # Find which child (if any) is currently selected
                sel_in_group = current if current in visible else None

                # Use a single radio for the whole group so labels render perfectly
                # Put a "— none —" sentinel at index 0 for when nothing in group is selected
                NONE = "__none__"
                opts = visible
                idx  = opts.index(sel_in_group) if sel_in_group in opts else None

                # Render each child as an individual button to keep indent styling clean
                st.sidebar.markdown("""
                <style>
                .nav-indent { margin-left: 12px; }
                </style>
                <div class="nav-indent">
                """, unsafe_allow_html=True)

                choice_in_group = st.sidebar.radio(
                    f"grp_radio_{_slugify(group_label)}",
                    opts,
                    index=idx if idx is not None else 0,
                    label_visibility="collapsed",
                    key=f"radio_{_slugify(group_label)}",
                )
                st.sidebar.markdown("</div>", unsafe_allow_html=True)

                # Sync selection
                if choice_in_group != current:
                    st.session_state[nav_key] = choice_in_group
                    st.rerun()

    return st.session_state.get(nav_key, menu_items[0])


def _nav_radio_item(label: str, current: str, nav_key: str) -> None:
    """Render a single top-level nav item as a one-item radio (preserves full label rendering)."""
    selected = current == label
    val = st.sidebar.radio(
        f"solo_{_slugify(label)}",
        [label],
        index=0,
        label_visibility="collapsed",
        key=f"radio_solo_{_slugify(label)}",
    )
    if val == label and current != label:
        st.session_state[nav_key] = label
        st.rerun()
