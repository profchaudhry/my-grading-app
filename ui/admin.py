import streamlit as st
from core.layout import base_console
from core.guards import require_role
from services.admin_service import AdminService
from services.department_service import DepartmentService
from services.semester_service import SemesterService
from services.course_service import CourseService
from ui.styles import section_header


@require_role(["admin"])
def admin_console() -> None:

    menu = base_console(
        "Admin Panel",
        [
            "📊 Dashboard",
            "🏛️ Departments",
            "📅 Semesters",
            "📚 Courses",
            "✅ Pending Approvals",
            "👥 Manage Users",
        ]
    )

    # ==============================================================
    # DASHBOARD
    # ==============================================================
    if menu == "📊 Dashboard":
        st.title("Admin Dashboard")

        metrics = AdminService.get_system_metrics()
        active_sem = SemesterService.get_active()

        if active_sem:
            st.info(f"📅 Active Semester: **{active_sem['name']}** "
                    f"({active_sem['start_date']} → {active_sem['end_date']})")
        else:
            st.warning("⚠️ No active semester set. Go to Semesters to activate one.")

        st.divider()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Users",  metrics["total_users"])
        col2.metric("Faculty",      metrics["faculty"])
        col3.metric("Students",     metrics["students"])
        col4.metric("Admins",       metrics["admins"])

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            section_header("Departments", "All registered departments")
            depts = DepartmentService.get_all()
            if depts:
                st.dataframe(
                    [{"Name": d["name"], "Code": d["code"]} for d in depts],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No departments yet.")

        with col_b:
            section_header("Semesters", "All academic terms")
            sems = SemesterService.get_all()
            if sems:
                st.dataframe(
                    [{
                        "Name": s["name"],
                        "Start": s["start_date"],
                        "End": s["end_date"],
                        "Active": "✅" if s["is_active"] else "—",
                    } for s in sems],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No semesters yet.")

    # ==============================================================
    # DEPARTMENTS
    # ==============================================================
    elif menu == "🏛️ Departments":
        st.title("🏛️ Departments")

        # Add department
        with st.expander("➕ Add New Department", expanded=False):
            with st.form("add_dept_form"):
                col1, col2 = st.columns(2)
                dept_name = col1.text_input("Department Name", placeholder="e.g. Computer Science")
                dept_code = col2.text_input("Code", placeholder="e.g. CS")
                if st.form_submit_button("Create Department", use_container_width=True):
                    if not dept_name or not dept_code:
                        st.warning("Both name and code are required.")
                    else:
                        if DepartmentService.create(dept_name, dept_code):
                            st.success(f"Department '{dept_name}' created.")
                            st.rerun()
                        else:
                            st.error("Failed to create department. Code may already exist.")

        st.divider()
        section_header("All Departments")

        depts = DepartmentService.get_all()
        if not depts:
            st.info("No departments found. Add one above.")
        else:
            for dept in depts:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    col1.write(f"**{dept['name']}**")
                    col2.write(f"`{dept['code']}`")

                    if col3.button("✏️ Edit", key=f"edit_dept_{dept['id']}"):
                        st.session_state[f"editing_dept_{dept['id']}"] = True

                    if col4.button("🗑️ Delete", key=f"del_dept_{dept['id']}"):
                        if DepartmentService.delete(dept["id"]):
                            st.success("Deleted.")
                            st.rerun()
                        else:
                            st.error("Delete failed.")

                    # Inline edit form
                    if st.session_state.get(f"editing_dept_{dept['id']}"):
                        with st.form(f"edit_dept_form_{dept['id']}"):
                            c1, c2 = st.columns(2)
                            new_name = c1.text_input("Name", value=dept["name"])
                            new_code = c2.text_input("Code", value=dept["code"])
                            s1, s2 = st.columns(2)
                            if s1.form_submit_button("Save", use_container_width=True):
                                if DepartmentService.update(dept["id"], new_name, new_code):
                                    del st.session_state[f"editing_dept_{dept['id']}"]
                                    st.success("Updated.")
                                    st.rerun()
                                else:
                                    st.error("Update failed.")
                            if s2.form_submit_button("Cancel", use_container_width=True):
                                del st.session_state[f"editing_dept_{dept['id']}"]
                                st.rerun()

                st.divider()

    # ==============================================================
    # SEMESTERS
    # ==============================================================
    elif menu == "📅 Semesters":
        st.title("📅 Semesters")

        with st.expander("➕ Add New Semester", expanded=False):
            with st.form("add_sem_form"):
                sem_name = st.text_input("Semester Name", placeholder="e.g. Fall 2025")
                col1, col2 = st.columns(2)
                start = col1.date_input("Start Date")
                end   = col2.date_input("End Date")
                if st.form_submit_button("Create Semester", use_container_width=True):
                    if not sem_name:
                        st.warning("Semester name is required.")
                    elif end <= start:
                        st.error("End date must be after start date.")
                    else:
                        if SemesterService.create(sem_name, str(start), str(end)):
                            st.success(f"Semester '{sem_name}' created.")
                            st.rerun()
                        else:
                            st.error("Failed. Name may already exist.")

        st.divider()
        section_header("All Semesters")

        sems = SemesterService.get_all()
        if not sems:
            st.info("No semesters found. Add one above.")
        else:
            for sem in sems:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                    col1.write(f"**{sem['name']}**")
                    col2.write(sem["start_date"])
                    col3.write(sem["end_date"])

                    if sem["is_active"]:
                        col4.markdown("✅ **Active**")
                    else:
                        if col4.button("Activate", key=f"act_sem_{sem['id']}"):
                            if SemesterService.set_active(sem["id"]):
                                st.success(f"'{sem['name']}' is now active.")
                                st.rerun()

                    if not sem["is_active"]:
                        if col5.button("🗑️", key=f"del_sem_{sem['id']}"):
                            if SemesterService.delete(sem["id"]):
                                st.rerun()
                st.divider()

    # ==============================================================
    # COURSES
    # ==============================================================
    elif menu == "📚 Courses":
        st.title("📚 Course Management")

        depts = DepartmentService.get_all()
        sems  = SemesterService.get_all()

        if not depts:
            st.warning("Please create at least one department first.")
            return
        if not sems:
            st.warning("Please create at least one semester first.")
            return

        dept_map = {d["name"]: d["id"] for d in depts}
        sem_map  = {s["name"]: s["id"] for s in sems}

        # Semester filter
        active_sem = SemesterService.get_active()
        sem_names  = [s["name"] for s in sems]
        default_sem = active_sem["name"] if active_sem else sem_names[0]
        selected_sem_name = st.selectbox(
            "Filter by Semester",
            sem_names,
            index=sem_names.index(default_sem) if default_sem in sem_names else 0,
            key="course_sem_filter"
        )
        selected_sem_id = sem_map[selected_sem_name]

        # Add course
        with st.expander("➕ Add New Course", expanded=False):
            with st.form("add_course_form"):
                col1, col2 = st.columns(2)
                c_name = col1.text_input("Course Name", placeholder="e.g. Data Structures")
                c_code = col2.text_input("Course Code", placeholder="e.g. CS201")

                col3, col4 = st.columns(2)
                c_dept = col3.selectbox("Department", list(dept_map.keys()))
                c_sem  = col4.selectbox("Semester", list(sem_map.keys()),
                                        index=list(sem_map.keys()).index(selected_sem_name)
                                        if selected_sem_name in sem_map else 0)

                col5, col6 = st.columns(2)
                c_credits  = col5.number_input("Credits", min_value=1, max_value=6, value=3)
                c_max_stud = col6.number_input("Max Students", min_value=1, max_value=300, value=40)

                c_desc = st.text_area("Description (optional)", height=80)

                if st.form_submit_button("Create Course", use_container_width=True):
                    if not c_name or not c_code:
                        st.warning("Course name and code are required.")
                    else:
                        if CourseService.create(
                            c_name, c_code,
                            dept_map[c_dept], sem_map[c_sem],
                            c_credits, c_max_stud, c_desc
                        ):
                            st.success(f"Course '{c_code} - {c_name}' created.")
                            st.rerun()
                        else:
                            st.error("Failed. Course code may already exist.")

        st.divider()

        # Fetch all faculty for assignment
        all_users  = AdminService.get_all_users()
        faculty_list = [u for u in all_users if u.get("role") == "faculty" and u.get("approved")]
        faculty_map = {
            f"{u.get('first_name','')} {u.get('last_name','')} ({u['email']})".strip(): u["id"]
            for u in faculty_list
        }

        courses = CourseService.get_all(selected_sem_id)
        section_header(
            f"Courses — {selected_sem_name}",
            f"{len(courses)} course(s) found"
        )

        if not courses:
            st.info("No courses for this semester. Add one above.")
        else:
            for course in courses:
                dept_name = (course.get("departments") or {}).get("name", "—")
                enrolled  = CourseService.get_enrollment_count(course["id"])

                with st.expander(
                    f"📘 {course['code']} — {course['name']}  "
                    f"| {dept_name} | {course['credits']} credits "
                    f"| {enrolled}/{course['max_students']} enrolled"
                ):
                    col1, col2 = st.columns(2)
                    col1.markdown(f"**Description:** {course.get('description') or '—'}")
                    col2.markdown(f"**Max Students:** {course['max_students']}")

                    st.markdown("**Assigned Faculty:**")
                    assigned = CourseService.get_assigned_faculty(course["id"])
                    if assigned:
                        for a in assigned:
                            p = a.get("profiles", {})
                            fname = f"{p.get('first_name','')} {p.get('last_name','')}".strip() or p.get("email", "—")
                            c1, c2 = st.columns([4, 1])
                            c1.write(f"👨‍🏫 {fname}")
                            if c2.button("Remove", key=f"unassign_{course['id']}_{a['faculty_id']}"):
                                CourseService.unassign_faculty(course["id"], a["faculty_id"])
                                st.rerun()
                    else:
                        st.caption("No faculty assigned yet.")

                    if faculty_map:
                        with st.form(f"assign_form_{course['id']}"):
                            sel_faculty = st.selectbox(
                                "Assign Faculty",
                                list(faculty_map.keys()),
                                key=f"sel_fac_{course['id']}"
                            )
                            if st.form_submit_button("Assign", use_container_width=True):
                                CourseService.assign_faculty(course["id"], faculty_map[sel_faculty])
                                st.success("Faculty assigned.")
                                st.rerun()

                    st.divider()
                    d1, d2 = st.columns(2)
                    if d2.button("🗑️ Delete Course", key=f"del_course_{course['id']}",
                                  type="secondary"):
                        if CourseService.delete(course["id"]):
                            st.success("Course deleted.")
                            st.rerun()

    # ==============================================================
    # PENDING APPROVALS
    # ==============================================================
    elif menu == "✅ Pending Approvals":
        st.title("✅ Faculty Pending Approval")

        pending = AdminService.get_pending_faculty()

        if not pending:
            st.success("No pending approvals at this time.")
        else:
            for user in pending:
                with st.container():
                    col1, col2, col3 = st.columns([5, 1, 1])
                    col1.write(f"📧 **{user.get('email')}**")

                    if col2.button("✅ Approve", key=f"approve_{user['id']}"):
                        if AdminService.approve_faculty(user["id"]):
                            st.success(f"Approved {user.get('email')}.")
                            st.rerun()
                        else:
                            st.error("Approval failed.")

                    if col3.button("❌ Reject", key=f"reject_{user['id']}"):
                        if AdminService.reject_faculty(user["id"]):
                            st.warning("Rejected and removed.")
                            st.rerun()
                        else:
                            st.error("Rejection failed.")
                st.divider()

    # ==============================================================
    # MANAGE USERS
    # ==============================================================
    elif menu == "👥 Manage Users":
        st.title("👥 Manage Users")

        from core.permissions import VALID_ROLES

        users = AdminService.get_all_users()
        if not users:
            st.info("No users found.")
        else:
            search = st.text_input("🔍 Search by email", placeholder="Type to filter...")
            filtered = [u for u in users if search.lower() in u.get("email", "").lower()] \
                       if search else users

            st.caption(f"Showing {len(filtered)} of {len(users)} users")
            st.divider()

            for user in filtered:
                with st.container():
                    col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                    col1.write(f"**{user.get('email', '—')}**")
                    col2.write(user.get("role", "—").capitalize())
                    approved = "✅ Active" if user.get("approved") else "⏳ Pending"
                    col3.write(approved)

                    current_role = user.get("role", "student")
                    try:
                        idx = VALID_ROLES.index(current_role)
                    except ValueError:
                        idx = 0

                    new_role = st.selectbox(
                        "Role",
                        VALID_ROLES,
                        index=idx,
                        key=f"role_{user['id']}",
                        label_visibility="collapsed",
                    )
                    if col4.button("Save", key=f"update_{user['id']}"):
                        if new_role == current_role:
                            st.info("Already set.")
                        elif AdminService.update_role(user["id"], new_role):
                            st.success("Updated.")
                            st.rerun()
                        else:
                            st.error("Failed.")
                st.divider()
