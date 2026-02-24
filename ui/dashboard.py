import streamlit as st
from services.faculty_service import FacultyService
from services.student_service import StudentService


def render_dashboard():
    role = st.session_state.role
    user = st.session_state.user

    if role == "faculty":
        data = FacultyService.get_profile(user.id)
    else:
        data = StudentService.get_profile(user.id)

    if not data:
        st.error("Profile not found.")
        return

    st.title("Dashboard")
    st.markdown(f"**Role:** {role}")
    st.markdown(
        f"**Name:** {data.get('first_name','')} {data.get('last_name','')}"
    )
