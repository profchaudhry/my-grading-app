import streamlit as st

# Logger must be imported first so basicConfig applies before any other module logs
import core.logger  # noqa: F401

from ui.styles import load_styles
from ui.login import login_page
from core.router import route

# ------------------------------------------------------------------
# Page configuration — must be the FIRST Streamlit call
# ------------------------------------------------------------------
st.set_page_config(
    page_title="SylemaX",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="auto",
)

load_styles()

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
# Routing
# ------------------------------------------------------------------
if st.session_state.user is None:
    login_page()
else:
    route(st.session_state.role)
