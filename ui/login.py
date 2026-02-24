import streamlit as st
from services.auth_service import AuthService
from services.faculty_service import FacultyService


def login_page():

    st.markdown('<div class="main-title">SylemaX</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Let\'s make academic management a breeze</div>',
        unsafe_allow_html=True
    )

    auth_mode = st.radio(
        "Select Option",
        ["Login", "Faculty Registration"],
        horizontal=True,
        key="auth_mode"
    )

    # ==========================
    # LOGIN FORM
    # ==========================
    if auth_mode == "Login":

        with st.form("login_form"):

            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")

            submitted = st.form_submit_button("Login")

            if submitted:

                if not login_email or not login_password:
                    st.warning("Please enter email and password.")
                else:
                    response = AuthService.login(login_email, login_password)

                    if not response or not response.user:
                        st.error("Invalid credentials.")
                    else:
                        user = response.user
                        profile = FacultyService.get_profile(user.id)

                        if not profile:
                            st.error("User profile not found. Contact admin.")
                        else:
                            st.session_state.user = user
                            st.session_state.role = profile["role"]
                            st.rerun()

    # ==========================
    # REGISTRATION FORM
    # ==========================
    else:

        with st.form("registration_form"):

            reg_email = st.text_input("Faculty Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")

            submitted = st.form_submit_button("Register Faculty")

            if submitted:

                if not reg_email or not reg_password:
                    st.warning("Please enter email and password.")
                else:
                    response = AuthService.register_faculty(reg_email, reg_password)

                    if response:
                        st.success("Registration submitted. Await admin approval.")
                    else:
                        st.error("Registration failed.")
