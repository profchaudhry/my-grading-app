import streamlit as st
from utils.db import supabase, load_courses, load_faculty

if st.session_state.profile["role"] not in ["admin", "faculty_pro"]:
    st.stop()

st.title("Admin Console")

menu = st.radio("Select", ["Manage Courses", "Assign Courses"])

if menu == "Manage Courses":

    code = st.text_input("Course Code")
    title = st.text_input("Course Title")
    semester = st.text_input("Semester")

    if st.button("Create"):
        supabase.table("courses").insert({
            "course_code": code,
            "course_title": title,
            "semester": semester
        }).execute()
        st.success("Course created.")

elif menu == "Assign Courses":

    faculty = load_faculty()
    courses = load_courses()

    faculty_map = {f["email"]: f["id"] for f in faculty}
    course_map = {c["course_code"]: c["id"] for c in courses}

    selected_faculty = st.selectbox("Faculty", list(faculty_map.keys()))
    selected_course = st.selectbox("Course", list(course_map.keys()))

    if st.button("Assign"):
        supabase.table("faculty_courses").insert({
            "faculty_id": faculty_map[selected_faculty],
            "course_id": course_map[selected_course]
        }).execute()
        st.success("Assigned.")
