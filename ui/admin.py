import streamlit as st
from core.layout import base_console
from core.guards import require_role
from services.admin_service import AdminService


@require_role(["admin"])
def admin_console():

    menu = base_console(
        "Admin Panel",
        [
            "Dashboard",
            "Pending Approvals",
            "Manage Users"
        ]
    )

    # ==============================
    # DASHBOARD
    # ==============================
    if menu == "Dashboard":

        st.title("Admin Dashboard")

        users = AdminService.get_all_users()
        total_users = len(users)
        total_faculty = len([u for u in users if u["role"] == "faculty"])
        total_students = len([u for u in users if u["role"] == "student"])

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Users", total_users)
        col2.metric("Faculty", total_faculty)
        col3.metric("Students", total_students)

    # ==============================
    # PENDING APPROVALS
    # ==============================
    if menu == "Pending Approvals":

        st.header("Faculty Pending Approval")

        pending = AdminService.get_pending_faculty()

        if not pending:
            st.success("No pending approvals.")
            return

        for user in pending:

            col1, col2 = st.columns([4,1])

            col1.write(f"{user['email']}")

            if col2.button("Approve", key=f"approve_{user['id']}"):
                AdminService.approve_faculty(user["id"])
                st.success("Faculty approved.")
                st.rerun()

    # ==============================
    # MANAGE USERS
    # ==============================
    if menu == "Manage Users":

        st.header("All Users")

        users = AdminService.get_all_users()

        for user in users:

            col1, col2, col3 = st.columns([4,2,2])

            col1.write(user["email"])
            col2.write(user["role"])

            new_role = col3.selectbox(
                "Change Role",
                ["admin", "faculty", "student"],
                index=["admin", "faculty", "student"].index(user["role"]),
                key=f"role_{user['id']}"
            )

            if new_role != user["role"]:
                if st.button("Update", key=f"update_{user['id']}"):
                    AdminService.update_role(user["id"], new_role)
                    st.success("Role updated.")
                    st.rerun()
