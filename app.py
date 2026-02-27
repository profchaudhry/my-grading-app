import streamlit as st

# Logger must be imported first so basicConfig applies before any other module logs
import core.logger  # noqa: F401

from ui.styles import inject_global_css
from ui.login import login_page
from core.router import route

# ------------------------------------------------------------------
# Page configuration — must be the FIRST Streamlit call
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Sylemax",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

# ------------------------------------------------------------------
# Session state initialization
# ------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "role" not in st.session_state:
    st.session_state.role = None

if "profile" not in st.session_state:
    st.session_state.profile = None

# ------------------------------------------------------------------
# Session persistence — restore from query params on refresh
# ------------------------------------------------------------------
if st.session_state.user is None:
    params = st.query_params
    access_token  = params.get("at",  None)
    refresh_token = params.get("rt",  None)

    if access_token and refresh_token:
        from services.auth_service import AuthService
        result = AuthService.restore_session(access_token, refresh_token)
        if result and result.get("user"):
            profile = result.get("profile", {}) or {}
            st.session_state.user    = result["user"]
            st.session_state.role    = profile.get("role", "student")
            st.session_state.profile = profile
            # Refresh tokens may have rotated — update params silently
            st.query_params["at"] = result.get("access_token",  access_token)
            st.query_params["rt"] = result.get("refresh_token", refresh_token)
            st.rerun()
        else:
            # Tokens expired/invalid — clear and show login
            st.query_params.clear()

# ------------------------------------------------------------------
# Routing
# ------------------------------------------------------------------
if st.session_state.user is None:
    login_page()
else:
    route(st.session_state.role)
