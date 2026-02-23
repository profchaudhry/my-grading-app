def route(role):

    if role == "admin":
        from ui.admin import admin_console
        admin_console()

    elif role == "faculty":
        from ui.faculty import faculty_console
        faculty_console()

    elif role == "student":
        from ui.student import student_console
        student_console()

    else:
        import streamlit as st
        st.error("Invalid role configuration.")
