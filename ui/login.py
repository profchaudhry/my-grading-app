import streamlit as st
from services.auth_service import AuthService


def login_page() -> None:
    """
    Renders the login form and handles authentication.
    On success, stores user/role in session state and reruns.
    Also provides a faculty registration flow.
    """
    st.markdown('<p class="main-title">🎓 SylemaX</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Academic Grading System</p>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Login", "Faculty Registration"])

    # ------------------------------------------------------------------
    # LOGIN TAB
    # ------------------------------------------------------------------
    with tab_login:
        st.subheader("Sign In")

        email = st.text_input("Email", key="login_email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_button", use_container_width=True):
            if not email or not password:
                st.warning("Please enter both email and password.")
                return

            with st.spinner("Authenticating..."):
                response = AuthService.login(email.strip(), password)

            if not response or not response.get("user"):
                st.error("Invalid credentials. Please check your email and password.")
                return

            user = response["user"]
            profile = response["profile"]

            st.session_state.user = user
            st.session_state.role = profile.get("role", "student")
            st.session_state.profile = profile

            st.success(f"Welcome back, {user.email}!")
            st.rerun()

    # ------------------------------------------------------------------
    # FACULTY REGISTRATION TAB
    # ------------------------------------------------------------------
    with tab_register:
        st.subheader("Faculty Registration")
        st.info("Faculty accounts require admin approval before access is granted.")

        reg_email = st.text_input("Email", key="reg_email", placeholder="faculty@example.com")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

        if st.button("Register as Faculty", key="register_button", use_container_width=True):
            if not reg_email or not reg_password or not reg_confirm:
                st.warning("All fields are required.")
                return

            if reg_password != reg_confirm:
                st.error("Passwords do not match.")
                return

            if len(reg_password) < 8:
                st.error("Password must be at least 8 characters.")
                return

            with st.spinner("Submitting registration..."):
                success = AuthService.register_faculty(reg_email.strip(), reg_password)

            if success:
                st.success("Registration submitted! An admin will review your account.")
            else:
                st.error("Registration failed. This email may already be registered.")
