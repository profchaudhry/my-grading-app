import streamlit as st
from core.layout import base_console
from core.guards import require_role

@require_role(["admin"])
def admin_console():

    menu = base_console("Admin Panel", ["Dashboard"])

    if menu == "Dashboard":
        st.title("Admin Dashboard")
        st.info("Admin features coming soon.")
