import streamlit as st
from ui.styles import inject_global_css, render_sidebar_logo, render_sidebar_user
from typing import List


def base_console(title: str, menu_items: List[str]) -> str:
    inject_global_css()

    role    = st.session_state.get("role", "")
    user    = st.session_state.get("user")
    profile = st.session_state.get("profile", {}) or {}

    # ── Display name ─────────────────────────────────────────────
    if role == "student" and profile.get("full_name", "").strip():
        display_name = profile["full_name"].strip()
    else:
        first = profile.get("first_name", "").strip()
        last  = profile.get("last_name",  "").strip()
        display_name = f"{first} {last}".strip() or (user.email if user else "User")

    render_sidebar_logo()
    render_sidebar_user(display_name, role)

    # ── Section label style ───────────────────────────────────────
    st.sidebar.markdown("""
    <style>
    .nav-section {
        font-size: 9.5px;
        font-weight: 700;
        color: rgba(255,255,255,0.40);
        text-transform: uppercase;
        letter-spacing: 1.4px;
        padding: 8px 4px 2px 4px;
        margin: 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────
    if role == "admin":
        choice = _render_admin_nav(menu_items)
    else:
        st.sidebar.markdown('<p class="nav-section">Navigation</p>',
                            unsafe_allow_html=True)
        choice = st.sidebar.radio(
            "nav", menu_items,
            label_visibility="collapsed",
            key=f"nav_{role}",
        )

    # ── Logout ────────────────────────────────────────────────────
    st.sidebar.divider()
    st.sidebar.markdown("""
    <style>
    /* Target the logout button specifically by key */
    [data-testid="stSidebar"] [data-testid="baseButton-secondary"]:has(+ *) {
        display: none;
    }
    /* Simple approach: style ALL secondary buttons in sidebar that come after divider */
    section[data-testid="stSidebar"] .stButton button {
        /* keep existing radio styling untouched */
    }
    /* Logout specifically */
    section[data-testid="stSidebar"] .logout-area .stButton > button {
        background: rgba(255,255,255,0.12) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.28) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        transition: background 0.15s;
    }
    section[data-testid="stSidebar"] .logout-area .stButton > button:hover {
        background: rgba(210,40,40,0.32) !important;
        border-color: rgba(255,90,90,0.50) !important;
    }
    </style>
    <div class="logout-area">
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        from services.auth_service import AuthService
        AuthService.logout()
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    return choice


def _render_admin_nav(menu_items: List[str]) -> str:
    """
    Admin navigation: flat st.sidebar.radio with markdown group headers.
    One single radio widget = one selection state = same pill style as faculty.
    """
    item_set = set(menu_items)

    top      = [i for i in ["📊 Dashboard"] if i in item_set]
    academic = [i for i in ["🏛️ Departments", "📅 Semesters", "📚 Courses"]
                if i in item_set]
    users    = [i for i in ["👨‍🏫 Faculty", "🎓 Students", "✅ Pending Approvals",
                             "📋 Enrollment", "📋 Bulk Enrollment"]
                if i in item_set]
    tools    = [i for i in ["📒 Gradebook", "🏆 UPro Grade", "📈 Reports",
                             "📣 Communications", "🔒 Change Password"]
                if i in item_set]

    all_items = top + academic + users + tools

    nav_key = "nav_admin"
    if nav_key not in st.session_state or st.session_state[nav_key] not in item_set:
        st.session_state[nav_key] = all_items[0]

    current_idx = all_items.index(st.session_state[nav_key])

    def _section(label: str) -> None:
        st.sidebar.markdown(f'<p class="nav-section">{label}</p>',
                            unsafe_allow_html=True)

    # Render sections with headers then one combined radio
    # The radio covers ALL items in order — headers are cosmetic only
    _section("Menu")

    choice = st.sidebar.radio(
        "admin_nav",
        all_items,
        index=current_idx,
        label_visibility="collapsed",
        key=nav_key,
    )

    return choice
