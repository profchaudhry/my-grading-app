import streamlit as st

def base_console(title, menu_items):

    st.sidebar.title(title)
    choice = st.sidebar.radio("", menu_items)

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    return choice
