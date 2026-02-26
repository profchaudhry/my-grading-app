"""
Shared UI components used across student, faculty, and admin consoles.
"""
import streamlit as st
from services.profile_service import ProfileService
from ui.styles import section_header


def render_change_password() -> None:
    """
    Renders a change password form.
    Requires current password + new password + confirm.
    Works for all roles.
    """
    section_header("🔒 Change Password")

    user  = st.session_state.get("user")
    email = user.email if user else ""

    with st.form("change_password_form", clear_on_submit=True):
        current  = st.text_input("Current Password",  type="password", key="cp_current")
        new_pass = st.text_input("New Password",      type="password", key="cp_new")
        confirm  = st.text_input("Confirm New Password", type="password", key="cp_confirm")
        submitted = st.form_submit_button("Update Password", use_container_width=True)

    if submitted:
        if not current or not new_pass or not confirm:
            st.error("All fields are required.")
            return
        if new_pass == current:
            st.error("New password must be different from current password.")
            return
        if len(new_pass) < 8:
            st.error("New password must be at least 8 characters.")
            return
        if new_pass != confirm:
            st.error("New passwords do not match.")
            return

        with st.spinner("Updating password..."):
            success, error = ProfileService.change_password(current, new_pass, email)

        if success:
            st.success("✅ Password updated successfully.")
        else:
            st.error(f"❌ {error}")
