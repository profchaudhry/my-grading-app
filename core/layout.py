import streamlit as st
from ui.styles import inject_global_css, render_sidebar_logo, render_sidebar_user
from typing import List


def base_console(title: str, menu_items: List[str]) -> str:
    inject_global_css()

    role    = st.session_state.get("role", "")
    user    = st.session_state.get("user")
    profile = st.session_state.get("profile", {}) or {}

    # ── Display name ──────────────────────────────────────────────
    if role == "student" and profile.get("full_name", "").strip():
        display_name = profile["full_name"].strip()
    else:
        first = profile.get("first_name", "").strip()
        last  = profile.get("last_name",  "").strip()
        display_name = f"{first} {last}".strip() or (user.email if user else "User")

    render_sidebar_logo()
    render_sidebar_user(display_name, role)

    # ── Shared section header style ───────────────────────────────
    st.sidebar.markdown("""
    <style>
    .nav-group-label {
        font-size: 9px;
        font-weight: 800;
        color: rgba(255,255,255,0.38);
        text-transform: uppercase;
        letter-spacing: 1.6px;
        padding: 10px 6px 3px 6px;
        margin: 0;
        line-height: 1;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────
    if role == "admin":
        choice = _render_admin_nav(menu_items)
    else:
        st.sidebar.markdown('<p class="nav-group-label">Navigation</p>',
                            unsafe_allow_html=True)
        choice = st.sidebar.radio(
            "nav", menu_items,
            label_visibility="collapsed",
            key=f"nav_{role}",
        )

    # ── Logout ────────────────────────────────────────────────────
    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    # Inject logout styling scoped to a unique key attribute
    st.sidebar.markdown("""
    <style>
    [data-testid="stSidebar"] [data-testid="baseButton-secondary"]:not([data-active]) {
        /* don't break radio buttons */
    }
    /* Target logout by its label text via aria — most reliable */
    [data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {
        background: rgba(255,255,255,0.13) !important;
        color: #ffffff !important;
        border: 1.5px solid rgba(255,255,255,0.28) !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover {
        background: rgba(200,40,40,0.30) !important;
        border-color: rgba(255,80,80,0.50) !important;
        color: #ffffff !important;
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
    Admin nav with visual group sections using markdown headers
    between a single flat radio — same pill style as faculty.
    """
    item_set = set(menu_items)

    # Ordered group definitions
    groups = [
        (None,              ["📊 Dashboard"]),
        ("🎓 Academic Ops", ["🏛️ Departments", "📅 Semesters", "📚 Courses"]),
        ("👥 User Control", ["👨‍🏫 Faculty", "🎓 Students", "✅ Pending Approvals",
                              "📋 Enrollment", "📋 Bulk Enrollment"]),
        (None,              ["📒 Gradebook", "🏆 UPro Grade", "📈 Reports",
                              "📣 Communications", "🔒 Change Password"]),
    ]

    # Build flat ordered list keeping only items that exist in menu_items
    all_items = []
    for _, members in groups:
        all_items += [m for m in members if m in item_set]

    if not all_items:
        all_items = menu_items

    nav_key = "nav_admin"
    if nav_key not in st.session_state or st.session_state[nav_key] not in item_set:
        st.session_state[nav_key] = all_items[0]

    current_idx = all_items.index(st.session_state[nav_key]) \
                  if st.session_state[nav_key] in all_items else 0

    # Render group label before first item of each named group
    # We pass all_items as a single radio — headers are injected via markdown
    # BEFORE the radio renders. We split into per-group radios but sync state.

    # Approach: one radio per group section, keep state in nav_key
    current = st.session_state[nav_key]
    new_choice = current

    for group_label, members in groups:
        visible = [m for m in members if m in item_set]
        if not visible:
            continue

        if group_label:
            st.sidebar.markdown(
                f'<p class="nav-group-label">{group_label}</p>',
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                '<p class="nav-group-label">Menu</p>',
                unsafe_allow_html=True,
            )

        # Which item in this group is selected (if any)
        sel_in_group = current if current in visible else visible[0]
        idx = visible.index(sel_in_group) if sel_in_group in visible else 0

        group_key = f"nav_grp_{'_'.join(str(hash(m))[-4:] for m in visible[:2])}"
        picked = st.sidebar.radio(
            group_label or "main",
            visible,
            index=idx,
            label_visibility="collapsed",
            key=group_key,
        )

        # If user clicked an item in this group, update master choice
        if picked in visible and picked != current:
            new_choice = picked

    # Sync back to master key and rerun if changed
    if new_choice != current:
        st.session_state[nav_key] = new_choice
        st.rerun()

    return st.session_state[nav_key]
