import streamlit as st
from utils.auth import login

st.set_page_config(page_title="Sylemas UCS1.4", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    login()
    st.stop()

profile = st.session_state.profile

st.sidebar.success(f"Logged in as: {profile['email']}")
st.sidebar.info(f"Role: {profile['role']}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.profile = None
    st.rerun()

st.title("🎓 Welcome to Sylemas UCS1.4")
st.write("Use the left sidebar to navigate.")

