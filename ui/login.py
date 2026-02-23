import streamlit as st
from services.supabase_client import supabase

def login_page():

    st.markdown('<div class="main-title">SylemaX</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Let\'s make academic management a breeze</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:

        tab1, tab2 = st.tabs(["Login", "Faculty Registration"])

        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login"):
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })

                    user = response.user

                    profile = supabase.table("profiles")\
                        .select("*")\
                        .eq("id", user.id)\
                        .single()\
                        .execute()

                    st.session_state.user = user
                    st.session_state.role = profile.data["role"]
                    st.rerun()

                except:
                    st.error("Invalid credentials")

        with tab2:
            email = st.text_input("Faculty Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")

            if st.button("Register Faculty"):
                try:
                    response = supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })

                    supabase.table("profiles").insert({
                        "id": response.user.id,
                        "email": email,
                        "role": "faculty",
                        "approved": False
                    }).execute()

                    st.success("Registration submitted for approval.")

                except:
                    st.error("Registration failed.")
