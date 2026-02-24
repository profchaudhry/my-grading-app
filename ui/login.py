import streamlit as st
from services.auth_service import AuthService
from services.faculty_service import FacultyService


def login_page():

    st.markdown('<div class="main-title">SylemaX</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Let\'s make academic management a breeze</div>',
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["Login", "Faculty Registration"])

    # ==========================
    # LOGIN TAB
    # ==========================
    with tab1:

        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_btn"):

            if not login_email or not login_password:
                st.warning("Please enter email and password.")
                return

            response = AuthService.login(login_email, login_password)

            if not response or not response.user:
                st.error("Invalid credentials.")
                return

            user = response.user

            profile = FacultyService.get_profile(user.id)

            if not profile:
                st.error("User profile not found. Contact admin.")
                return

            st.session_state.user = user
            st.session_state.role = profile["role"]

            st.rerun()

    # ==========================
    # FACULTY REGISTRATION TAB
    # ==========================
    with tab2:

        reg_email = st.text_input("Faculty Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")

        if st.button("Register Faculty", key="register_btn"):

            if not reg_email or not reg_password:
                st.warning("Please enter email and password.")
                return

            response = AuthService.register_faculty(reg_email, reg_password)

            if response:
                st.success("Registration submitted. Await admin approval.")
