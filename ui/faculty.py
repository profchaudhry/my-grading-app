import streamlit as st
from services.faculty_service import (
    get_assigned_courses,
    get_profile,
    update_profile
)
from ui.dashboard import render_dashboard

def faculty_console():

    st.sidebar.title("Faculty Panel")

    menu = st.sidebar.radio(
        "",
        ["Dashboard", "My Courses", "My Profile"]
    )

    if menu == "Dashboard":
        render_dashboard()

    if menu == "My Courses":
        st.header("Assigned Courses")
        courses = get_assigned_courses(st.session_state.user.id)
        st.dataframe(courses)

    if menu == "My Profile":
        st.header("Profile")

        profile = get_profile(st.session_state.user.id)

        first = st.text_input("First Name", profile.get("first_name",""))
        last = st.text_input("Last Name", profile.get("last_name",""))
        designation = st.text_input("Designation", profile.get("designation",""))
        department = st.text_input("Department", profile.get("department",""))

        if st.button("Update Profile"):
            update_profile(st.session_state.user.id, {
                "first_name": first,
                "last_name": last,
                "designation": designation,
                "department": department
            })
            st.success("Profile Updated")
            st.cache_data.clear()
