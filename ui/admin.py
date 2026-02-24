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

    # ==========================================================
    # DASHBOARD
    # ==========================================================
    if menu == "Dashboard":

        st.title("Admin Dashboard")

        metrics = AdminService.get_system_metrics()

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Users", metrics["total_users"])
        col2.metric("Faculty", metrics["faculty"])
        col3.metric("Students", metrics["students"])
        col4.metric("Admins", metrics["admins"])

        st.divider()

        st.subheader("System Overview")

        users = AdminService.get_all_users()
        if users:
            st.dataframe(users, use_container_width=True)
        else:
            st.info("No users found in system.")

    # ==========================================================
    # PENDING APPROVALS
    # ==========================================================
    if menu == "Pending Approvals":

        st.header("Faculty Pending Approval")

        pending = AdminService.get_pending_faculty()

        if not pending:
            st.success("No pending approvals.")
            return

        for user in pending:

            col1, col2, col3 = st.columns([4, 1, 1])

            col1.write(f"📧 {user['email']}")

            if col2.button("Approve", key=f"approve_{user['id']}"):
                success = AdminService.approve_faculty(user["id"])
                if success:
                    st.success("Faculty approved.")
                    st.rerun()
                else:
                    st.error("Approval failed.")

            if col3.button("Reject", key=f"reject_{user['id']}"):
                success = AdminService.reject_faculty(user["id"])
                if success:
                    st.warning("Faculty rejected and removed.")
                    st.rerun()
                else:
                    st.error("Rejection failed.")

    # ==========================================================
    # MANAGE USERS
    # ==========================================================
    if menu == "Manage Users":

        st.header("All Users")

        users = AdminService.get_all_users()

        if not users:
            st.info("No users available.")
            return

        for user in users:

            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])

            col1.write(user["email"])
            col2.write(user["role"])

            roles = ["admin", "faculty", "student"]

            try:
                current_index = roles.index(user["role"])
            except ValueError:
                current_index = 0

            new_role = col3.selectbox(
                "Change Role",
                roles,
                index=current_index,
                key=f"role_{user['id']}"
            )

            if new_role != user["role"]:
                if col4.button("Update", key=f"update_{user['id']}"):
                    success = AdminService.update_role(user["id"], new_role)
                    if success:
                        st.success("Role updated.")
                        st.rerun()
                    else:
                        st.error("Role update failed.")
