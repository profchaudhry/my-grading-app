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

    # Section label CSS
    st.sidebar.markdown("""
    <style>
    .nav-section-lbl {
        font-size: 9px; font-weight: 800;
        color: rgba(255,255,255,0.38);
        text-transform: uppercase; letter-spacing: 1.6px;
        padding: 10px 6px 2px 6px; margin: 0; line-height: 1;
        display: block;
    }
    /* Logout button */
    section[data-testid="stSidebar"] button[kind="secondary"],
    section[data-testid="stSidebar"] .stButton > button {
        /* intentionally blank — let global styles handle radio pills */
    }
    </style>
    """, unsafe_allow_html=True)

    # Navigation
    if role == "admin":
        choice = _render_admin_nav(menu_items)
    else:
        st.sidebar.markdown('<span class="nav-section-lbl">Navigation</span>',
                            unsafe_allow_html=True)
        choice = st.sidebar.radio(
            "nav", menu_items,
            label_visibility="collapsed",
            key=f"nav_{role}",
        )

    # Logout
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <style>
    /* Logout: target the last stButton in the sidebar */
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
    <div class="logout-wrap">
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        from services.auth_service import AuthService
        AuthService.logout()
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    return choice


# Group membership for visual separators
_GROUPS = {
    "🎓 Academic Ops": {"🏛️ Departments", "📅 Semesters", "📚 Courses"},
    "👥 User Control": {"👨‍🏫 Faculty", "🎓 Students", "✅ Pending Approvals",
                        "📋 Enrollment", "📋 Bulk Enrollment"},
}

# First item of each group — where we inject the header
_GROUP_FIRST = {
    "🏛️ Departments":  "🎓 Academic Ops",
    "👨‍🏫 Faculty":     "👥 User Control",
}


def _render_admin_nav(menu_items: List[str]) -> str:
    """
    Single st.sidebar.radio — zero reruns, zero syncing.
    Group headers injected as markdown immediately before the radio
    using a container trick: render header markdown, then the radio below it.
    
    Since we can't inject markdown *between* radio options, we use
    format_func to prepend a unicode section marker to the first item
    of each group, making the grouping visually clear.
    """

    # Ordered items
    ORDER = [
        "📊 Dashboard",
        "🏛️ Departments", "📅 Semesters", "📚 Courses",
        "👨‍🏫 Faculty", "🎓 Students", "✅ Pending Approvals",
        "📋 Enrollment", "📋 Bulk Enrollment",
        "📒 Gradebook", "🏆 UPro Grade", "📈 Reports",
        "📣 Communications", "🔒 Change Password",
    ]
    ordered = [i for i in ORDER if i in set(menu_items)]
    # Append any items not in ORDER
    ordered += [i for i in menu_items if i not in set(ORDER)]

    nav_key = "nav_admin"

    # Inject group headers as markdown ABOVE the whole radio block,
    # and use format_func to add visual separators inside the list
    st.sidebar.markdown('<span class="nav-section-lbl">Menu</span>',
                        unsafe_allow_html=True)

    def fmt(item: str) -> str:
        # Prepend a faint separator line to first item of named groups
        if item == "🏛️ Departments":
            return f"╌ Academic Ops\n{item}"  # \n renders as space in radio label
        if item == "👨‍🏫 Faculty":
            return f"╌ User Control\n{item}"
        return item

    choice = st.sidebar.radio(
        "admin_nav",
        ordered,
        label_visibility="collapsed",
        key=nav_key,
        format_func=fmt,
    )

    return choice
