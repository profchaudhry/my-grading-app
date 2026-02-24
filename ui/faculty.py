import streamlit as st
from core.layout import base_console
from core.guards import require_role, require_approval
from services.faculty_service import FacultyService
from ui.dashboard import render_dashboard


@require_role(["faculty"])
def faculty_console() -> None:
    """Faculty portal with dashboard, courses, and profile management."""

    user = st.session_state.user
    profile = FacultyService.get_profile(user.id)

    # Block unapproved faculty before rendering anything else
    require_approval(profile)

    if not profile:
        st.error("Your profile could not be loaded. Please contact support.")
        return

    menu = base_console("👨‍🏫 Faculty Panel", ["Dashboard", "My Courses", "My Profile"])

    # ------------------------------------------------------------------
    # DASHBOARD
    # ------------------------------------------------------------------
    if menu == "Dashboard":
        render_dashboard()

    # ------------------------------------------------------------------
    # MY COURSES
    # ------------------------------------------------------------------
    elif menu == "My Courses":
        st.title("📚 My Courses")
        with st.spinner("Loading courses..."):
            courses = FacultyService.get_assigned_courses(user.id)

        if not courses:
            st.info("No courses are currently assigned to you.")
        else:
            st.dataframe(courses, use_container_width=True)

    # ------------------------------------------------------------------
    # MY PROFILE
    # ------------------------------------------------------------------
    elif menu == "My Profile":
        st.title("👤 My Profile")

        with st.form("profile_form"):
            first = st.text_input("First Name", value=profile.get("first_name", ""))
            last = st.text_input("Last Name", value=profile.get("last_name", ""))
            submitted = st.form_submit_button("Update Profile", use_container_width=True)

        if submitted:
            if not first.strip() and not last.strip():
                st.warning("Please enter at least a first or last name.")
            else:
                success = FacultyService.update_profile(
                    user.id,
                    {"first_name": first.strip(), "last_name": last.strip()}
                )
                if success:
                    st.success("Profile updated successfully.")
                    st.rerun()
                else:
                    st.error("Update failed. Please try again.")
