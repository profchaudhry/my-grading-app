import streamlit as st
from ui.dashboard import render_dashboard

def student_console():

    st.sidebar.title("Student Panel")

    menu = st.sidebar.radio(
        "",
        ["Dashboard"]
    )

    if menu == "Dashboard":
        render_dashboard()
