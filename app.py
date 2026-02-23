import streamlit as st
from ui.styles import load_styles
from ui.login import login_page
from core.router import route
import core.logger

st.set_page_config(page_title="SylemaX", layout="wide")

load_styles()

if "user" not in st.session_state:
    st.session_state.user = None

if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.user is None:
    login_page()
else:
    route(st.session_state.role)
