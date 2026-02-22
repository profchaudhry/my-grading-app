import streamlit as st
from utils.db import supabase, get_profile

def login():
    st.header("🔐 Login")

    role_selected = st.selectbox(
        "Login As",
        ["Student", "Faculty", "Admin", "Faculty Pro"]
    )

    if role_selected == "Student":
        username = st.text_input("Enrollment Number")
    else:
        username = st.text_input("Email")

    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role_selected == "Student":
            login_email = f"{username}@student.local"
        else:
            login_email = username

        response = supabase.auth.sign_in_with_password({
            "email": login_email,
            "password": password
        })

        if response.user:
            profile = get_profile(response.user.id)

            if not profile:
                st.error("Profile not found.")
                st.stop()

            expected_role = role_selected.lower().replace(" ", "_")

            if profile["role"] != expected_role:
                st.error("Incorrect role selected.")
                st.stop()

            st.session_state.user = response.user
            st.session_state.profile = profile
            st.rerun()
        else:
            st.error("Invalid credentials")
