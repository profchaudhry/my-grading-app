import streamlit as st
from core.permissions import VALID_ROLES


def route(role: str | None) -> None:
    """
    Routes the authenticated user to the correct console based on their role.
    Handles None and unknown roles gracefully.
    """
    if not role:
        st.error("No role found in session. Please log in again.")
        if st.button("Return to Login"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    if role not in VALID_ROLES:
        st.error(f"Unknown role '{role}'. Please contact an administrator.")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    if role == "admin":
        from ui.admin import admin_console
        admin_console()

    elif role == "faculty":
        from ui.faculty import faculty_console
        faculty_console()

    elif role == "student":
        from ui.student import student_console
        student_console()
