import streamlit as st
from core.layout import base_console
from core.guards import require_role, require_approval
from services.faculty_service import FacultyService
from ui.dashboard import render_dashboard

@require_role(["faculty"])
def faculty_console():

    menu = base_console("Faculty Panel", ["Dashboard", "My Courses", "My Profile"])

    if menu == "Dashboard":
        render_dashboard()

    if menu == "My Courses":
        courses = FacultyService.get_assigned_courses(st.session_state.user.id)
        st.dataframe(courses)

    if menu == "My Profile":
        profile = FacultyService.get_profile(st.session_state.user.id)
        require_approval(profile)

        first = st.text_input("First Name", profile.get("first_name",""))
        last = st.text_input("Last Name", profile.get("last_name",""))

        if st.button("Update"):
            FacultyService.update_profile(
                st.session_state.user.id,
                {"first_name": first, "last_name": last}
            )
            st.success("Updated")
