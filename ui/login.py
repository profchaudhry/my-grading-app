import streamlit as st
from services.auth_service import AuthService
from services.supabase_client import supabase
import logging

logger = logging.getLogger("sylemax.login")


def _change_password_screen() -> None:
    """Forced password change screen for first-time / reset logins."""
    st.markdown('<p class="main-title">🎓 SylemaX</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Academic Management System</p>', unsafe_allow_html=True)
    st.warning("🔒 You are using a temporary password. Please set a new password to continue.")

    with st.form("force_change_form"):
        new_pass = st.text_input("New Password",      type="password")
        confirm  = st.text_input("Confirm Password",  type="password")
        submitted = st.form_submit_button("Set New Password", use_container_width=True)

    if submitted:
        if not new_pass or not confirm:
            st.error("Both fields are required.")
            return
        if new_pass == "ChangeYourPassword":
            st.error("You cannot reuse the temporary password.")
            return
        if len(new_pass) < 8:
            st.error("Password must be at least 8 characters.")
            return
        if new_pass != confirm:
            st.error("Passwords do not match.")
            return
        try:
            supabase.auth.update_user({"password": new_pass})
            user = st.session_state.get("user")
            if user:
                supabase.table("profiles")\
                    .update({"force_password_change": False})\
                    .eq("id", user.id)\
                    .execute()
                if st.session_state.get("profile"):
                    st.session_state.profile["force_password_change"] = False
            st.success("✅ Password updated successfully!")
            st.rerun()
        except Exception as e:
            logger.exception("Forced password change failed.")
            st.error(f"Failed to update password: {str(e)}")


def login_page() -> None:
    # Check if logged-in user must change password
    if st.session_state.get("user") and st.session_state.get("profile"):
        if st.session_state.profile.get("force_password_change"):
            _change_password_screen()
            return

    st.markdown('<p class="main-title">🎓 SylemaX</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Academic Management System</p>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Login", "Faculty Registration"])

    # ── LOGIN ──────────────────────────────────────────────────────
    with tab_login:
        st.subheader("Sign In")
        st.caption("Students: use your enrollment email (e.g. 01-11111-011@um.ar)")

        email    = st.text_input("Email", key="login_email", placeholder="you@example.com")
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

            user    = response["user"]
            profile = response["profile"]

            st.session_state.user    = user
            st.session_state.role    = profile.get("role", "student")
            st.session_state.profile = profile

            if profile.get("force_password_change"):
                st.rerun()
                return

            st.rerun()

    # ── FACULTY REGISTRATION ───────────────────────────────────────
    with tab_register:
        st.subheader("Faculty Registration")
        st.info("Faculty accounts require admin approval. "
                "Students cannot self-register — accounts are created by admin.")

        c1, c2      = st.columns(2)
        reg_first   = c1.text_input("First Name",   key="reg_first",
                                     placeholder="e.g. John")
        reg_last    = c2.text_input("Last Name",    key="reg_last",
                                     placeholder="e.g. Smith")
        reg_emp_id  = st.text_input("Employee ID",  key="reg_emp_id",
                                     placeholder="e.g. EMP-001")
        reg_email   = st.text_input("Email",        key="reg_email",
                                     placeholder="faculty@university.edu")
        reg_pass    = st.text_input("Password",     type="password", key="reg_password")
        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

        if st.button("Register as Faculty", key="register_button", use_container_width=True):
            if not reg_first or not reg_last:
                st.warning("First and last name are required.")
                return
            if not reg_emp_id:
                st.warning("Employee ID is required.")
                return
            if not reg_email or not reg_pass or not reg_confirm:
                st.warning("Email and password fields are required.")
                return
            if reg_pass != reg_confirm:
                st.error("Passwords do not match.")
                return
            if len(reg_pass) < 8:
                st.error("Password must be at least 8 characters.")
                return

            with st.spinner("Submitting registration..."):
                success = AuthService.register_faculty(
                    email=reg_email.strip(),
                    password=reg_pass,
                    first_name=reg_first.strip(),
                    last_name=reg_last.strip(),
                    employee_id=reg_emp_id.strip(),
                )

            if success:
                st.success("Registration submitted! An admin will review your account.")
            else:
                st.error("Registration failed. This email may already be registered.")
