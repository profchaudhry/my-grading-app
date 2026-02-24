import streamlit as st
from services.faculty_service import FacultyService
from services.student_service import StudentService


def render_dashboard() -> None:
    """
    Renders a role-aware dashboard. Displays profile info and a welcome message.
    Handles missing profiles gracefully without crashing.
    """
    role = st.session_state.get("role")
    user = st.session_state.get("user")

    if not user or not role:
        st.error("Session data is missing. Please log in again.")
        return

    if role == "faculty":
        data = FacultyService.get_profile(user.id)
    else:
        data = StudentService.get_profile(user.id)

    st.title("📊 Dashboard")

    if not data:
        st.warning("Profile data could not be loaded. Please contact support.")
        return

    first = data.get("first_name", "").strip()
    last = data.get("last_name", "").strip()
    full_name = f"{first} {last}".strip() or user.email

    col1, col2 = st.columns(2)
    col1.markdown(f"**👤 Name:** {full_name}")
    col2.markdown(f"**🎭 Role:** {role.capitalize()}")

    st.divider()
    st.markdown(f"### Welcome back, {first or user.email}!")

    if role == "student":
        st.info("Use the sidebar to navigate your courses and grades.")
    elif role == "faculty":
        st.info("Use the sidebar to manage your courses and profile.")
