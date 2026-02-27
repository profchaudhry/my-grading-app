import streamlit as st
import core.logger  # noqa: F401

from ui.styles import inject_global_css
from ui.login import login_page
from core.router import route

# Page config — must be FIRST Streamlit call
st.set_page_config(
    page_title="Sylemax",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

# ── Session state init ────────────────────────────────────────────
for key in ("user", "role", "profile"):
    if key not in st.session_state:
        st.session_state[key] = None

# ── Restore session from URL tokens on refresh ────────────────────
if st.session_state.user is None:
    params        = st.query_params
    access_token  = params.get("at", None)
    refresh_token = params.get("rt", None)

    if access_token and refresh_token:
        from services.auth_service import AuthService
        result = AuthService.restore_session(access_token, refresh_token)
        if result and result.get("user"):
            profile = result.get("profile", {}) or {}
            st.session_state.user    = result["user"]
            st.session_state.role    = profile.get("role", "student")
            st.session_state.profile = profile
            st.query_params["at"]    = result.get("access_token",  access_token)
            st.query_params["rt"]    = result.get("refresh_token", refresh_token)
            st.rerun()
        else:
            st.query_params.clear()

# ── Routing ───────────────────────────────────────────────────────
if st.session_state.user is None:
    login_page()
else:
    user    = st.session_state.user
    role    = st.session_state.role or "student"
    user_id = user.id

    # Global comms widgets (marquee ticker + login popup)
    try:
        from ui.communications import render_comms_widgets
        from services.supabase_client import supabase
        enrolled_r = supabase.table("enrollments")\
            .select("course_id")\
            .eq("student_id", user_id)\
            .eq("status", "active")\
            .execute()
        enrolled_ids = [e["course_id"] for e in (enrolled_r.data or [])]
        render_comms_widgets(user_id, role, enrolled_ids)
    except Exception:
        pass  # Never let comms crash the app

    route(role)
