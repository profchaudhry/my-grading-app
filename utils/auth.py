import streamlit as st
from utils.db import supabase, get_profile


# ==========================
# LOGIN PAGE
# ==========================
def login():

    st.title("UCS Login")

    role_selected = st.selectbox(
        "Select Role",
        ["Student", "Faculty", "Admin"]
    )

    username = st.text_input(
        "Enrollment Number" if role_selected == "Student" else "Email"
    )

    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    # ========================================
    # STUDENT LOGIN
    # ========================================
    if role_selected == "Student":

        with col1:
            if st.button("Login"):

                if not username or not password:
                    st.error("Enter enrollment number and password.")
                    st.stop()

                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": f"{username}@student.local",
                        "password": password
                    })
                except Exception as e:
                    st.error("Invalid login credentials.")
                    st.stop()

                if response.user:

                    profile = get_profile(response.user.id)

                    if not profile:
                        st.error("Profile not found. Contact admin.")
                        st.stop()

                    st.session_state.user = response.user
                    st.session_state.profile = profile
                    st.rerun()

    # ========================================
    # FACULTY LOGIN
    # ========================================
    if role_selected == "Faculty":

        with col1:
            if st.button("Login"):

                if not username or not password:
                    st.error("Enter email and password.")
                    st.stop()

                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": username,
                        "password": password
                    })
                except Exception:
                    st.error("Invalid login credentials.")
                    st.stop()

                if response.user:

                    profile = get_profile(response.user.id)

                    if not profile:
                        st.error("Profile not found. Contact admin.")
                        st.stop()

                    if profile["role"] == "pending_faculty":
                        st.warning("Awaiting admin approval.")
                        st.stop()

                    st.session_state.user = response.user
                    st.session_state.profile = profile
                    st.rerun()

        # ========================================
        # FACULTY REGISTRATION
        # ========================================
        with col2:
            if st.button("Register as Faculty"):

                if not username or not password:
                    st.error("Enter email and password.")
                    st.stop()

                try:
                    response = supabase.auth.sign_up({
                        "email": username,
                        "password": password
                    })
                except Exception as e:
                    st.error(f"Registration Error: {str(e)}")
                    st.stop()

                if response.user:

                    profile = get_profile(response.user.id)

                    if not profile:
                        supabase.table("profiles").insert({
                            "id": response.user.id,
                            "email": username,
                            "role": "pending_faculty",
                            "must_change_password": False
                        }).execute()

                    st.success("Registration successful. Awaiting admin approval.")
                else:
                    st.error("Registration failed.")

    # ========================================
    # ADMIN LOGIN
    # ========================================
    if role_selected == "Admin":

        if st.button("Login"):

            if not username or not password:
                st.error("Enter email and password.")
                st.stop()

            try:
                response = supabase.auth.sign_in_with_password({
                    "email": username,
                    "password": password
                })
            except Exception:
                st.error("Invalid login credentials.")
                st.stop()

            if response.user:

                profile = get_profile(response.user.id)

                if not profile or profile["role"] not in ["admin", "faculty_pro"]:
                    st.error("Unauthorized access.")
                    st.stop()

                st.session_state.user = response.user
                st.session_state.profile = profile
                st.rerun()


# ==========================
# FORCE PASSWORD CHANGE
# ==========================
def enforce_password_change():

    profile = st.session_state.profile

    if profile.get("must_change_password"):

        st.warning("You must change your password.")

        new_pass = st.text_input("New Password", type="password")

        if st.button("Update Password"):

            if len(new_pass) < 6:
                st.error("Password too short.")
                st.stop()

            supabase.auth.update_user({
                "password": new_pass
            })

            supabase.table("profiles").update({
                "must_change_password": False
            }).eq("id", profile["id"]).execute()

            st.success("Password updated.")
            st.rerun()


# ==========================
# LOGOUT
# ==========================
def logout():

    if st.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()
