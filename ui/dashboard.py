import streamlit as st
from services.faculty_service import get_profile
from services.student_service import get_student_profile

def render_dashboard():

    user = st.session_state.user
    role = st.session_state.role

    if role == "student":
        data = get_student_profile(user.id)
    else:
        data = get_profile(user.id)

    st.title("Dashboard")
    st.markdown("### You are logged in as:")

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(f"**Role:** {role.capitalize()}")

    if role == "student":
        st.markdown(f"**Name:** {data.get('first_name','')} {data.get('last_name','')}")
        st.markdown(f"**Enrollment Number:** {data.get('enrollment','')}")
    else:
        st.markdown(f"**Name:** {data.get('first_name','')} {data.get('last_name','')}")
        st.markdown(f"**Email Address:** {data.get('email')}")

    st.markdown('</div>', unsafe_allow_html=True)
