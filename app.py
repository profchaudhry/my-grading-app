import streamlit as st
from ui.styles import load_styles
from ui.login import login_page
from ui.admin import admin_console
from ui.faculty import faculty_console
from ui.student import student_console

st.set_page_config(
    page_title="SylemaX",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_styles()

if "user" not in st.session_state:
    st.session_state.user = None

if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.user is None:
    login_page()
else:
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()

    role = st.session_state.role

    if role == "admin":
        admin_console()
    elif role == "faculty":
        faculty_console()
    elif role == "student":
        student_console()
