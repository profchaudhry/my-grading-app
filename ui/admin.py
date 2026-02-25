import streamlit as st
from core.layout import base_console
from core.guards import require_role
from core.permissions import VALID_ROLES
from services.admin_service import AdminService
from services.department_service import DepartmentService
from services.semester_service import SemesterService
from services.course_service import CourseService
from ui.styles import section_header


# ================================================================
# HELPERS
# ================================================================

def _full_name(profile: dict) -> str:
    first = profile.get("first_name", "") or ""
    last  = profile.get("last_name",  "") or ""
    return f"{first} {last}".strip() or profile.get("email", "—")


def _faculty_edit_form(user: dict, form_key: str) -> dict | None:
    """Renders a full faculty edit form. Returns submitted data dict or None."""
    with st.form(form_key):
        section_header("Credentials")
        c1, c2 = st.columns(2)
        first       = c1.text_input("First Name",   value=user.get("first_name", "") or "")
        last        = c2.text_input("Last Name",     value=user.get("last_name",  "") or "")
        employee_id = c1.text_input("Employee ID",   value=user.get("employee_id","") or "")
        qualification = c2.text_input("Qualification (e.g. PhD, MSc)",
                                       value=user.get("qualification","") or "")

        st.divider()
        section_header("Contact Information")
        c3, c4 = st.columns(2)
        phone   = c3.text_input("Phone Number",    value=user.get("phone","")  or "")
        office  = c4.text_input("Office Location", value=user.get("office_location","") or "")
        address = st.text_input("Address",          value=user.get("address","") or "")

        st.divider()
        section_header("Academic Information")
        specialization = st.text_input("Specialization / Subject Area",
                                        value=user.get("specialization","") or "")
        publications   = st.text_area("Publications",
                                       value=user.get("publications","") or "",
                                       height=100)

        st.divider()
        section_header("Account")
        c5, c6 = st.columns(2)
        role     = c5.selectbox("Role", VALID_ROLES,
                                 index=VALID_ROLES.index(user.get("role","faculty"))
                                 if user.get("role") in VALID_ROLES else 1)
        approved = c6.checkbox("Approved", value=bool(user.get("approved", False)))

        submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if submitted:
        return {
            "first_name":      first.strip(),
            "last_name":       last.strip(),
            "employee_id":     employee_id.strip(),
            "qualification":   qualification.strip(),
            "phone":           phone.strip(),
            "office_location": office.strip(),
            "address":         address.strip(),
            "specialization":  specialization.strip(),
            "publications":    publications.strip(),
            "role":            role,
            "approved":        approved,
        }
    return None


def _student_edit_form(user: dict, form_key: str) -> dict | None:
    """Renders a full student edit form. Returns submitted data dict or None."""
    with st.form(form_key):
        section_header("Credentials")
        c1, c2 = st.columns(2)
        first      = c1.text_input("First Name",  value=user.get("first_name","") or "")
        last       = c2.text_input("Last Name",   value=user.get("last_name", "") or "")
        student_id = c1.text_input("Student ID",  value=user.get("student_id","") or "")
        program    = c2.text_input("Program / Degree", value=user.get("program","") or "")

        c3, c4 = st.columns(2)
        year_of_study = c3.number_input(
            "Year of Study", min_value=1, max_value=10,
            value=int(user.get("year_of_study") or 1)
        )
        dob_val = user.get("date_of_birth")
        if dob_val:
            import datetime
            try:
                dob_val = datetime.date.fromisoformat(str(dob_val))
            except Exception:
                dob_val = None
        dob = c4.date_input("Date of Birth", value=dob_val)

        st.divider()
        section_header("Contact Information")
        c5, c6 = st.columns(2)
        phone   = c5.text_input("Phone Number", value=user.get("phone","")   or "")
        address = c6.text_input("Address",       value=user.get("address","") or "")

        st.divider()
        section_header("Account")
        role     = st.selectbox("Role", VALID_ROLES,
                                 index=VALID_ROLES.index(user.get("role","student"))
                                 if user.get("role") in VALID_ROLES else 2)

        submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if submitted:
        return {
            "first_name":    first.strip(),
            "last_name":     last.strip(),
            "student_id":    student_id.strip(),
            "program":       program.strip(),
            "year_of_study": year_of_study,
            "date_of_birth": str(dob) if dob else None,
            "phone":         phone.strip(),
            "address":       address.strip(),
            "role":          role,
        }
    return None


def _render_user_card(user: dict, role_type: str) -> None:
    """Renders a single user card with view/edit/delete controls."""
    uid       = user["id"]
    name      = _full_name(user)
    email     = user.get("email", "—")
    approved  = user.get("approved", False)
    edit_key  = f"editing_{uid}"
    status_icon = "✅" if approved else "⏳"

    with st.expander(f"{status_icon} **{name}** — {email}"):

        # ── View mode ──
        if not st.session_state.get(edit_key):
            if role_type == "faculty":
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Employee ID:** {user.get('employee_id','—') or '—'}")
                c2.markdown(f"**Phone:** {user.get('phone','—') or '—'}")
                c3.markdown(f"**Office:** {user.get('office_location','—') or '—'}")
                c1.markdown(f"**Qualification:** {user.get('qualification','—') or '—'}")
                c2.markdown(f"**Specialization:** {user.get('specialization','—') or '—'}")
                c3.markdown(f"**Approved:** {'Yes' if approved else 'No'}")
                if user.get("address"):
                    st.markdown(f"**Address:** {user['address']}")
                if user.get("publications"):
                    st.markdown(f"**Publications:** {user['publications']}")
            else:
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Student ID:** {user.get('student_id','—') or '—'}")
                c2.markdown(f"**Phone:** {user.get('phone','—') or '—'}")
                c3.markdown(f"**Program:** {user.get('program','—') or '—'}")
                c1.markdown(f"**Year:** {user.get('year_of_study','—') or '—'}")
                c2.markdown(f"**DOB:** {user.get('date_of_birth','—') or '—'}")
                if user.get("address"):
                    c3.markdown(f"**Address:** {user['address']}")

            st.divider()
            col_edit, col_del = st.columns(2)
            if col_edit.button("✏️ Edit Profile", key=f"edit_btn_{uid}",
                                use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()
            if col_del.button("🗑️ Delete User", key=f"del_btn_{uid}",
                               use_container_width=True, type="secondary"):
                st.session_state[f"confirm_delete_{uid}"] = True

            # Confirm delete
            if st.session_state.get(f"confirm_delete_{uid}"):
                st.warning(f"⚠️ Are you sure you want to permanently delete **{name}**?")
                yes, no = st.columns(2)
                if yes.button("Yes, Delete", key=f"confirm_yes_{uid}",
                               type="primary", use_container_width=True):
                    if AdminService.delete_user(uid):
                        st.success("User deleted.")
                        del st.session_state[f"confirm_delete_{uid}"]
                        st.rerun()
                    else:
                        st.error("Delete failed.")
                if no.button("Cancel", key=f"confirm_no_{uid}",
                              use_container_width=True):
                    del st.session_state[f"confirm_delete_{uid}"]
                    st.rerun()

        # ── Edit mode ──
        else:
            if role_type == "faculty":
                data = _faculty_edit_form(user, f"edit_form_{uid}")
            else:
                data = _student_edit_form(user, f"edit_form_{uid}")

            if data is not None:
                if AdminService.update_profile(uid, data):
                    st.success("Profile updated successfully.")
                    del st.session_state[edit_key]
                    st.rerun()
                else:
                    st.error("Update failed. Please try again.")

            if st.button("← Cancel", key=f"cancel_edit_{uid}"):
                del st.session_state[edit_key]
                st.rerun()


# ================================================================
# MAIN ADMIN CONSOLE
# ================================================================

@require_role(["admin"])
def admin_console() -> None:

    menu = base_console(
        "Admin Panel",
        [
            "📊 Dashboard",
            "🏛️ Departments",
            "📅 Semesters",
            "📚 Courses",
            "👨‍🏫 Faculty",
            "🎓 Students",
            "✅ Pending Approvals",
        ]
    )

    # ==============================================================
    # DASHBOARD
    # ==============================================================
    if menu == "📊 Dashboard":
        st.title("Admin Dashboard")

        metrics    = AdminService.get_system_metrics()
        active_sem = SemesterService.get_active()

        if active_sem:
            st.info(f"📅 Active Semester: **{active_sem['name']}**  "
                    f"({active_sem['start_date']} → {active_sem['end_date']})")
        else:
            st.warning("⚠️ No active semester set. Go to Semesters to activate one.")

        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Users", metrics["total_users"])
        col2.metric("Faculty",     metrics["faculty"])
        col3.metric("Students",    metrics["students"])
        col4.metric("Admins",      metrics["admins"])

        st.divider()
        col_a, col_b = st.columns(2)

        with col_a:
            section_header("Departments")
            depts = DepartmentService.get_all()
            if depts:
                st.dataframe(
                    [{"Department": d["name"],
                      "Campus": d.get("campus","—"),
                      "School": d.get("school","—"),
                      "HoD": d.get("hod_name","—")}
                     for d in depts],
                    use_container_width=True, hide_index=True,
                )
            else:
                st.info("No departments yet.")

        with col_b:
            section_header("Semesters")
            sems = SemesterService.get_all()
            if sems:
                st.dataframe(
                    [{"Name": s["name"],
                      "Start": s["start_date"],
                      "End": s["end_date"],
                      "Active": "✅" if s["is_active"] else "—"}
                     for s in sems],
                    use_container_width=True, hide_index=True,
                )
            else:
                st.info("No semesters yet.")

    # ==============================================================
    # DEPARTMENTS
    # ==============================================================
    elif menu == "🏛️ Departments":
        st.title("🏛️ Departments")

        with st.expander("➕ Add New Department", expanded=False):
            with st.form("add_dept_form"):
                c1, c2 = st.columns(2)
                d_campus  = c1.text_input("Campus",     placeholder="e.g. Main Campus")
                d_school  = c2.text_input("School",     placeholder="e.g. School of Engineering")
                d_dept    = st.text_input("Department", placeholder="e.g. Computer Science")
                c3, c4 = st.columns(2)
                d_hod_name  = c3.text_input("HoD Name",  placeholder="e.g. Dr. John Smith")
                d_hod_email = c4.text_input("HoD Email", placeholder="e.g. jsmith@university.edu")

                if st.form_submit_button("Create Department", use_container_width=True):
                    if not d_dept or not d_campus:
                        st.warning("Campus and Department are required.")
                    else:
                        if DepartmentService.create({
                            "name":       d_dept,
                            "campus":     d_campus,
                            "school":     d_school,
                            "department": d_dept,
                            "hod_name":   d_hod_name,
                            "hod_email":  d_hod_email,
                        }):
                            st.success(f"Department '{d_dept}' created.")
                            st.rerun()
                        else:
                            st.error("Failed to create department.")

        st.divider()
        section_header("All Departments")

        depts = DepartmentService.get_all()
        if not depts:
            st.info("No departments found. Add one above.")
        else:
            for dept in depts:
                with st.expander(
                    f"🏛️ **{dept['name']}** — {dept.get('campus','—')} | {dept.get('school','—')}"
                ):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Campus:** {dept.get('campus','—')}")
                    c2.markdown(f"**School:** {dept.get('school','—')}")
                    c1.markdown(f"**Department:** {dept.get('department','—')}")
                    c2.markdown(f"**HoD Name:** {dept.get('hod_name','—')}")
                    c1.markdown(f"**HoD Email:** {dept.get('hod_email','—')}")

                    st.divider()
                    edit_key = f"editing_dept_{dept['id']}"
                    col_e, col_d = st.columns(2)

                    if col_e.button("✏️ Edit", key=f"edit_dept_{dept['id']}",
                                     use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()

                    if col_d.button("🗑️ Delete", key=f"del_dept_{dept['id']}",
                                     use_container_width=True, type="secondary"):
                        if DepartmentService.delete(dept["id"]):
                            st.success("Deleted.")
                            st.rerun()
                        else:
                            st.error("Delete failed.")

                    if st.session_state.get(edit_key):
                        with st.form(f"edit_dept_form_{dept['id']}"):
                            c1, c2 = st.columns(2)
                            new_campus  = c1.text_input("Campus",     value=dept.get("campus",""))
                            new_school  = c2.text_input("School",     value=dept.get("school",""))
                            new_dept    = st.text_input("Department", value=dept.get("department",""))
                            c3, c4 = st.columns(2)
                            new_hod_name  = c3.text_input("HoD Name",  value=dept.get("hod_name",""))
                            new_hod_email = c4.text_input("HoD Email", value=dept.get("hod_email",""))
                            s1, s2 = st.columns(2)
                            if s1.form_submit_button("Save", use_container_width=True):
                                if DepartmentService.update(dept["id"], {
                                    "name":       new_dept,
                                    "campus":     new_campus,
                                    "school":     new_school,
                                    "department": new_dept,
                                    "hod_name":   new_hod_name,
                                    "hod_email":  new_hod_email,
                                }):
                                    del st.session_state[edit_key]
                                    st.success("Updated.")
                                    st.rerun()
                                else:
                                    st.error("Update failed.")
                            if s2.form_submit_button("Cancel", use_container_width=True):
                                del st.session_state[edit_key]
                                st.rerun()

    # ==============================================================
    # SEMESTERS
    # ==============================================================
    elif menu == "📅 Semesters":
        st.title("📅 Semesters")

        with st.expander("➕ Add New Semester", expanded=False):
            with st.form("add_sem_form"):
                sem_name = st.text_input("Semester Name", placeholder="e.g. Fall 2025")
                c1, c2   = st.columns(2)
                start    = c1.date_input("Start Date")
                end      = c2.date_input("End Date")
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
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
                    c1.write(f"**{sem['name']}**")
                    c2.write(sem["start_date"])
                    c3.write(sem["end_date"])
                    if sem["is_active"]:
                        c4.markdown("✅ **Active**")
                    else:
                        if c4.button("Activate", key=f"act_sem_{sem['id']}"):
                            if SemesterService.set_active(sem["id"]):
                                st.success(f"'{sem['name']}' is now active.")
                                st.rerun()
                    if not sem["is_active"]:
                        if c5.button("🗑️", key=f"del_sem_{sem['id']}"):
                            SemesterService.delete(sem["id"])
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

        active_sem    = SemesterService.get_active()
        sem_names     = list(sem_map.keys())
        default_sem   = active_sem["name"] if active_sem and active_sem["name"] in sem_names else sem_names[0]
        sel_sem_name  = st.selectbox("Filter by Semester", sem_names,
                                      index=sem_names.index(default_sem), key="course_sem_filter")
        sel_sem_id    = sem_map[sel_sem_name]

        with st.expander("➕ Add New Course", expanded=False):
            with st.form("add_course_form"):
                c1, c2   = st.columns(2)
                c_name   = c1.text_input("Course Name", placeholder="e.g. Data Structures")
                c_code   = c2.text_input("Course Code", placeholder="e.g. CS201")
                c3, c4   = st.columns(2)
                c_dept   = c3.selectbox("Department", list(dept_map.keys()))
                c_sem    = c4.selectbox("Semester", sem_names,
                                         index=sem_names.index(sel_sem_name))
                c5, c6   = st.columns(2)
                c_credits   = c5.number_input("Credits",      min_value=1, max_value=6, value=3)
                c_max_stud  = c6.number_input("Max Students", min_value=1, max_value=300, value=40)
                c_desc   = st.text_area("Description (optional)", height=80)

                if st.form_submit_button("Create Course", use_container_width=True):
                    if not c_name or not c_code:
                        st.warning("Course name and code are required.")
                    else:
                        if CourseService.create(
                            c_name, c_code, dept_map[c_dept],
                            sem_map[c_sem], c_credits, c_max_stud, c_desc
                        ):
                            st.success(f"Course '{c_code} — {c_name}' created.")
                            st.rerun()
                        else:
                            st.error("Failed. Course code may already exist.")

        st.divider()

        all_users    = AdminService.get_all_users()
        faculty_list = [u for u in all_users if u.get("role") == "faculty" and u.get("approved")]
        faculty_map  = {
            f"{_full_name(u)} ({u['email']})": u["id"]
            for u in faculty_list
        }

        courses = CourseService.get_all(sel_sem_id)
        section_header(f"Courses — {sel_sem_name}", f"{len(courses)} course(s)")

        if not courses:
            st.info("No courses for this semester. Add one above.")
        else:
            for course in courses:
                dept_name = (course.get("departments") or {}).get("name", "—")
                enrolled  = CourseService.get_enrollment_count(course["id"])
                with st.expander(
                    f"📘 {course['code']} — {course['name']}  "
                    f"| {dept_name} | {course['credits']} cr "
                    f"| {enrolled}/{course['max_students']} enrolled"
                ):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Description:** {course.get('description') or '—'}")
                    c2.markdown(f"**Max Students:** {course['max_students']}")

                    st.markdown("**Assigned Faculty:**")
                    assigned = CourseService.get_assigned_faculty(course["id"])
                    if assigned:
                        for a in assigned:
                            p     = a.get("profiles", {})
                            fname = _full_name(p) if p else "—"
                            ca, cb = st.columns([5, 1])
                            ca.write(f"👨‍🏫 {fname}")
                            if cb.button("Remove", key=f"unassign_{course['id']}_{a['faculty_id']}"):
                                CourseService.unassign_faculty(course["id"], a["faculty_id"])
                                st.rerun()
                    else:
                        st.caption("No faculty assigned yet.")

                    if faculty_map:
                        with st.form(f"assign_form_{course['id']}"):
                            sel_f = st.selectbox("Assign Faculty", list(faculty_map.keys()),
                                                  key=f"sel_fac_{course['id']}")
                            if st.form_submit_button("Assign", use_container_width=True):
                                CourseService.assign_faculty(course["id"], faculty_map[sel_f])
                                st.success("Faculty assigned.")
                                st.rerun()

                    st.divider()
                    if st.button("🗑️ Delete Course", key=f"del_course_{course['id']}",
                                  type="secondary"):
                        if CourseService.delete(course["id"]):
                            st.success("Deleted.")
                            st.rerun()

    # ==============================================================
    # FACULTY MANAGEMENT
    # ==============================================================
    elif menu == "👨‍🏫 Faculty":
        st.title("👨‍🏫 Faculty Management")

        faculty = AdminService.get_faculty_users()

        if not faculty:
            st.info("No faculty members registered yet.")
        else:
            search = st.text_input("🔍 Search by name or email", key="faculty_search",
                                    placeholder="Type to filter...")
            if search:
                faculty = [
                    u for u in faculty
                    if search.lower() in u.get("email","").lower()
                    or search.lower() in _full_name(u).lower()
                ]

            approved_f = [u for u in faculty if u.get("approved")]
            pending_f  = [u for u in faculty if not u.get("approved")]

            st.caption(f"{len(faculty)} total · {len(approved_f)} approved · {len(pending_f)} pending")
            st.divider()

            if pending_f:
                section_header("⏳ Pending Approval", f"{len(pending_f)} faculty awaiting approval")
                for user in pending_f:
                    _render_user_card(user, "faculty")
                st.divider()

            if approved_f:
                section_header("✅ Active Faculty", f"{len(approved_f)} faculty members")
                for user in approved_f:
                    _render_user_card(user, "faculty")

    # ==============================================================
    # STUDENT MANAGEMENT
    # ==============================================================
    elif menu == "🎓 Students":
        st.title("🎓 Student Management")

        students = AdminService.get_student_users()

        if not students:
            st.info("No students registered yet.")
        else:
            search = st.text_input("🔍 Search by name, email, or student ID",
                                    key="student_search", placeholder="Type to filter...")
            if search:
                students = [
                    u for u in students
                    if search.lower() in u.get("email","").lower()
                    or search.lower() in _full_name(u).lower()
                    or search.lower() in (u.get("student_id","") or "").lower()
                ]

            st.caption(f"{len(students)} student(s) found")
            st.divider()

            for user in students:
                _render_user_card(user, "student")

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
                    c1, c2, c3 = st.columns([5, 1, 1])
                    c1.write(f"📧 **{user.get('email')}**")
                    if c2.button("✅ Approve", key=f"approve_{user['id']}"):
                        if AdminService.approve_faculty(user["id"]):
                            st.success(f"Approved {user.get('email')}.")
                            st.rerun()
                        else:
                            st.error("Approval failed.")
                    if c3.button("❌ Reject", key=f"reject_{user['id']}"):
                        if AdminService.reject_faculty(user["id"]):
                            st.warning("Rejected and removed.")
                            st.rerun()
                        else:
                            st.error("Rejection failed.")
                st.divider()
