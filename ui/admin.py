import streamlit as st
from core.layout import base_console
from core.guards import require_role
from core.permissions import VALID_ROLES
from services.admin_service import AdminService


@require_role(["admin"])
def admin_console() -> None:
    """Admin portal — metrics, faculty approvals, and user role management."""

    menu = base_console(
        "🛡️ Admin Panel",
        ["Dashboard", "Pending Approvals", "Manage Users"]
    )

    # ------------------------------------------------------------------
    # DASHBOARD
    # ------------------------------------------------------------------
    if menu == "Dashboard":
        st.title("🛡️ Admin Dashboard")

        with st.spinner("Loading metrics..."):
            metrics = AdminService.get_system_metrics()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Users", metrics["total_users"])
        col2.metric("Faculty", metrics["faculty"])
        col3.metric("Students", metrics["students"])
        col4.metric("Admins", metrics["admins"])

        st.divider()
        st.subheader("All Users")

        with st.spinner("Loading users..."):
            users = AdminService.get_all_users()

        if users:
            st.dataframe(users, use_container_width=True)
        else:
            st.info("No users found in the system.")

    # ------------------------------------------------------------------
    # PENDING APPROVALS
    # ------------------------------------------------------------------
    elif menu == "Pending Approvals":
        st.title("🕐 Faculty Pending Approval")

        with st.spinner("Fetching pending faculty..."):
            pending = AdminService.get_pending_faculty()

        if not pending:
            st.success("✅ No pending approvals at this time.")
        else:
            for user in pending:
                with st.container():
                    col1, col2, col3 = st.columns([5, 1, 1])
                    col1.write(f"📧 {user.get('email', 'Unknown')}")

                    if col2.button("✅ Approve", key=f"approve_{user['id']}"):
                        if AdminService.approve_faculty(user["id"]):
                            st.success(f"Approved {user.get('email')}.")
                            st.rerun()
                        else:
                            st.error("Approval failed. Please try again.")

                    if col3.button("❌ Reject", key=f"reject_{user['id']}"):
                        if AdminService.reject_faculty(user["id"]):
                            st.warning(f"Rejected and removed {user.get('email')}.")
                            st.rerun()
                        else:
                            st.error("Rejection failed. Please try again.")

                st.divider()

    # ------------------------------------------------------------------
    # MANAGE USERS
    # ------------------------------------------------------------------
    elif menu == "Manage Users":
        st.title("👥 Manage Users")

        with st.spinner("Loading users..."):
            users = AdminService.get_all_users()

        if not users:
            st.info("No users available.")
        else:
            for user in users:
                with st.container():
                    col1, col2, col3, col4 = st.columns([4, 2, 2, 1])

                    col1.write(user.get("email", "—"))
                    col2.write(f"**{user.get('role', '—')}**")

                    current_role = user.get("role", "student")
                    try:
                        current_index = VALID_ROLES.index(current_role)
                    except ValueError:
                        current_index = 0

                    new_role = col3.selectbox(
                        "Role",
                        VALID_ROLES,
                        index=current_index,
                        key=f"role_{user['id']}",
                        label_visibility="collapsed",
                    )

                    # Always show the button; validate on click
                    if col4.button("Save", key=f"update_{user['id']}"):
                        if new_role == current_role:
                            st.info("Role is already set to that value.")
                        else:
                            if AdminService.update_role(user["id"], new_role):
                                st.success(f"Role updated to '{new_role}'.")
                                st.rerun()
                            else:
                                st.error("Role update failed.")

                st.divider()
