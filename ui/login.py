import streamlit as st
from services.auth_service import AuthService
from services.faculty_service import FacultyService

def login_page():
    st.markdown('<div class="main-title">SylemaX</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Let\'s make academic management a breeze</div>', unsafe_allow_html=True)

    auth_mode = st.radio("Select Option", ["Login", "Faculty Registration"], horizontal=True, key="auth_mode")

    # ==========================
    # LOGIN FORM
    # ==========================
    if auth_mode == "Login":
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if not email or not password:
                    st.warning("Please enter email and password.")
                else:
                    response = AuthService.login(email, password)
                    if not response or not response["user"]:
                        st.error("Invalid credentials.")
                    elif not response["profile"]:
                        st.error("Profile not found. Contact admin.")
                    else:
                        st.session_state.user = response["user"]
                        st.session_state.role = response["profile"]["role"]
                        st.rerun()

    # ==========================
    # FACULTY REGISTRATION
    # ==========================
    else:
        with st.form("registration_form"):
            email = st.text_input("Faculty Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            submitted = st.form_submit_button("Register Faculty")
            if submitted:
                if not email or not password:
                    st.warning("Please enter email and password.")
                else:
                    response = AuthService.register_faculty(email, password)
                    if response:
                        st.success("Registration submitted. Await admin approval.")
                    else:
                        st.error("Registration failed.")
