import streamlit as st
from services.auth_service import AuthService
from services.supabase_client import supabase


def login_page():

    st.markdown('<div class="main-title">SylemaX</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Let\'s make academic management a breeze</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Faculty Registration"])

    # ==========================================================
    # LOGIN TAB
    # ==========================================================
    with tab1:

        with st.form("login_form", clear_on_submit=False):

            login_email = st.text_input("Email", key="login_email_input")
            login_password = st.text_input("Password", type="password", key="login_password_input")

            login_submit = st.form_submit_button("Login")

            if login_submit:

                if not login_email or not login_password:
                    st.warning("Please enter email and password.")
                    return

                try:
                    response = AuthService.login(login_email, login_password)

                    if not response or not response.user:
                        st.error("Invalid credentials.")
                        return

                    user = response.user

                    # ------------------------------------------------------
                    # SAFE PROFILE FETCH (NO .single() CRASH)
                    # ------------------------------------------------------
                    profile_res = (
                        supabase
                        .table("profiles")
                        .select("*")
                        .eq("id", user.id)
                        .maybe_single()
                        .execute()
                    )

                    profile = profile_res.data

                    # ------------------------------------------------------
                    # AUTO-CREATE PROFILE IF MISSING
                    # ------------------------------------------------------
                    if profile is None:
                        # Default role logic
                        default_role = "student"

                        supabase.table("profiles").insert({
                            "id": user.id,
                            "email": login_email,
                            "role": default_role,
                            "approved": True
                        }).execute()

                        profile = {
                            "id": user.id,
                            "email": login_email,
                            "role": default_role,
                            "approved": True
                        }

                    # ------------------------------------------------------
                    # SESSION SETUP
                    # ------------------------------------------------------
                    st.session_state.user = user
                    st.session_state.role = profile["role"]

                    st.rerun()

                except Exception as e:
                    st.error("Login failed. Please check configuration.")
                    return

    # ==========================================================
    # FACULTY REGISTRATION TAB
    # ==========================================================
    with tab2:

        with st.form("registration_form", clear_on_submit=False):

            reg_email = st.text_input("Faculty Email", key="reg_email_input")
            reg_password = st.text_input("Password", type="password", key="reg_password_input")

            reg_submit = st.form_submit_button("Register Faculty")

            if reg_submit:

                if not reg_email or not reg_password:
                    st.warning("Please fill all fields.")
                    return

                try:
                    response = AuthService.register_faculty(reg_email, reg_password)

                    if response and response.user:
                        st.success("Registration submitted for approval.")
                    else:
                        st.error("Registration failed.")

                except Exception:
                    st.error("Registration error. Check configuration.")
