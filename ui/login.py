import streamlit as st
from services.auth_service import AuthService
from services.faculty_service import FacultyService

def login_page():

    st.markdown('<div class="main-title">SylemaX</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Let\'s make academic management a breeze</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Faculty Registration"])

    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            response = AuthService.login(email, password)

            user = response.user
            profile = FacultyService.get_profile(user.id)

            st.session_state.user = user
            st.session_state.role = profile["role"]
            st.rerun()

    with tab2:
        email = st.text_input("Faculty Email")
        password = st.text_input("Password", type="password")

        if st.button("Register Faculty"):
            AuthService.register_faculty(email, password)
            st.success("Registration submitted.")
