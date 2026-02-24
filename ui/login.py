import streamlit as st
from services.auth_service import AuthService

def login_page():
    st.title("Login")

    login_email = st.text_input("Email", key="login_email")
    login_password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_button"):

        if not login_email or not login_password:
            st.warning("Please enter email and password.")
            return

        # ===================== DEBUG CODE =====================
        # Check if app is connected to correct Supabase project
        try:
            user_info = supabase.auth.get_user()  # returns current logged-in user info
            st.write("DEBUG: Supabase current user info:", user_info)
        except Exception as e:
            st.error(f"DEBUG ERROR: Cannot fetch user from Supabase: {e}")
        # =======================================================

        response = AuthService.login(login_email, login_password)

        if not response or not response.get("user"):
            st.error("Invalid credentials. Check email/password or project connection.")
            return

        st.success(f"Logged in as {response['user'].email}")

        st.session_state.user = response["user"]
        st.session_state.role = response["profile"].get("role", "student")

        st.experimental_rerun()
