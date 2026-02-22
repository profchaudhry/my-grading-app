import streamlit as st
from utils.db import supabase, get_profile

def login():
    st.header("🔐 Sylemas Login / Registration")

    role_selected = st.selectbox(
        "Login As",
        ["Student", "Faculty", "Admin", "Faculty Pro"]
    )

    # Input fields
    if role_selected == "Student":
        username = st.text_input("Enrollment Number")
    else:
        username = st.text_input("Email")

    password = st.text_input("Password", type="password")

    col1, col2 = st.columns([1,1])

    # Faculty registration button (only visible if Faculty)
    if role_selected == "Faculty":
        with col1:
            if st.button("Register as Faculty"):
                if not username or not password:
                    st.error("Enter email and password.")
                else:
                    # Register user in Supabase Auth
                    response = supabase.auth.sign_up({
                        "email": username,
                        "password": password
                    })

                    if response.user:
                        # Create profile as pending
                        supabase.table("profiles").insert({
                            "id": response.user.id,
                            "email": username,
                            "role": "pending_faculty",
                            "must_change_password": False
                        }).execute()

                        st.success("Registration successful. Waiting for Admin approval.")
                    else:
                        st.error("Registration failed. Try again.")

    # Login button
    with col2:
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
