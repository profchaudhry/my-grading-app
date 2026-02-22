import streamlit as st
from utils.db import load_students

if st.session_state.profile["role"] != "student":
    st.stop()

st.title("Student Dashboard")

students = load_students()
enrollment = st.session_state.profile["enrollment"]

student = students[students["enrollment"] == enrollment].iloc[0]

email = st.text_input("Email", value=student.get("email", ""))
phone = st.text_input("Phone", value=student.get("phone", ""))

if st.button("Update"):
    from utils.db import supabase
    supabase.table("students")\
        .update({"email": email, "phone": phone})\
        .eq("enrollment", enrollment)\
        .execute()
    st.success("Updated.")
