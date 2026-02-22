import streamlit as st
from utils.db import supabase

if st.session_state.profile["role"] not in ["faculty", "faculty_pro"]:
    st.stop()

st.title("Faculty Console")

menu = st.radio("Select", ["My Profile", "My Courses"])

if menu == "My Profile":

    existing = supabase.table("faculty_profiles")\
        .select("*")\
        .eq("id", st.session_state.user.id)\
        .execute()

    data = existing.data[0] if existing.data else {}

    first = st.text_input("First Name", value=data.get("first_name", ""))
    last = st.text_input("Last Name", value=data.get("last_name", ""))

    if st.button("Save"):
        supabase.table("faculty_profiles").upsert({
            "id": st.session_state.user.id,
            "first_name": first,
            "last_name": last
        }).execute()

        st.success("Saved.")

elif menu == "My Courses":

    assigned = supabase.table("faculty_courses")\
        .select("courses(*)")\
        .eq("faculty_id", st.session_state.user.id)\
        .execute()

    if assigned.data:
        for c in assigned.data:
            st.write(c["courses"]["course_code"])
    else:
        st.warning("No courses assigned.")
