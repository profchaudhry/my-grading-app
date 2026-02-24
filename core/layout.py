import streamlit as st
from typing import List


def base_console(title: str, menu_items: List[str]) -> str:
    """
    Renders a sidebar with a title, radio menu, and logout button.
    Returns the currently selected menu item.
    """
    st.sidebar.title(title)
    choice = st.sidebar.radio("Navigation", menu_items, label_visibility="collapsed")

    st.sidebar.divider()

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    return choice
