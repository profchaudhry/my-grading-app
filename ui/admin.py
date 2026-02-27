import streamlit as st
import pandas as pd
from core.layout import base_console
from core.guards import require_role
from core.permissions import VALID_ROLES
from services.admin_service import AdminService
from services.department_service import DepartmentService
from services.semester_service import SemesterService
from services.course_service import CourseService
from services.enrollment_service import EnrollmentService
from services.student_bulk_service import StudentBulkService
from services.profile_service import ProfileService
from services.supabase_client import supabase
from ui.styles import section_header
from ui.components import render_change_password
from ui.admin_gradebook import render_admin_gradebook
from ui.reports import render_admin_reports
from ui.communications import render_admin_communications
from ui.upro_grade import render_upro_grade
from ui.bulk_enrollment import render_bulk_enrollment
import logging

logger = logging.getLogger("sylemax.admin_ui")


# ================================================================
# HELPERS
# ================================================================

def _full_name(profile: dict) -> str:
    """Prefers full_name field (used for students); falls back to first+last (faculty/admin)."""
    full = (profile.get("full_name") or "").strip()
    if full:
        return full
    first = (profile.get("first_name") or "").strip()
    last  = (profile.get("last_name")  or "").strip()
    return f"{first} {last}".strip() or profile.get("email", "—")


def _faculty_edit_form(user: dict, form_key: str) -> dict | None:
    """
    Admin can edit ALL faculty fields including first/last name and employee ID.
    """
    with st.form(form_key):
        section_header("Identity (Admin Only)")
        c1, c2 = st.columns(2)
        first         = c1.text_input("First Name",  value=user.get("first_name","") or "")
        last          = c2.text_input("Last Name",   value=user.get("last_name", "") or "")
        employee_id   = c1.text_input("Employee ID", value=user.get("employee_id","") or "")
        qualification = c2.text_input("Qualification (e.g. PhD, MSc)",
                                       value=user.get("qualification","") or "")
        st.divider()
        section_header("Contact Information")
        c3, c4 = st.columns(2)
        phone   = c3.text_input("Phone Number",    value=user.get("phone","") or "")
        office  = c4.text_input("Office Location", value=user.get("office_location","") or "")
        address = st.text_input("Address",          value=user.get("address","") or "")
        st.divider()
        section_header("Academic Information")
        specialization = st.text_input("Specialization / Subject Area",
                                        value=user.get("specialization","") or "")
        publications   = st.text_area("Publications",
                                       value=user.get("publications","") or "", height=80)
        st.divider()
        section_header("Account")
        c5, c6   = st.columns(2)
        role     = c5.selectbox("Role", VALID_ROLES,
                                 index=VALID_ROLES.index(user.get("role","faculty"))
                                 if user.get("role") in VALID_ROLES else 1)
        approved = c6.checkbox("Approved", value=bool(user.get("approved", False)))
        submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if submitted:
        return {
            "first_name": first.strip(), "last_name": last.strip(),
            "employee_id": employee_id.strip(), "qualification": qualification.strip(),
            "phone": phone.strip(), "office_location": office.strip(),
            "address": address.strip(), "specialization": specialization.strip(),
            "publications": publications.strip(), "role": role, "approved": approved,
        }
    return None


def _student_edit_form(user: dict, form_key: str) -> dict | None:
    """Admin can edit ALL student fields."""
    # Derive full_name display value
    existing_full = (user.get("full_name","") or "").strip() or                     f"{user.get('first_name','') or ''} {user.get('last_name','') or ''}".strip()
    with st.form(form_key):
        section_header("Identity (Admin Only)")
        c1, c2 = st.columns(2)
        full_name_val = c1.text_input("Full Name", value=existing_full)
        enrollment_no = c2.text_input("Enrollment Number",
                                       value=user.get("enrollment_number","") or "")
        program       = c1.text_input("Program / Degree", value=user.get("program","") or "")
        c3, c4 = st.columns(2)
        year_of_study = c3.number_input("Year of Study", min_value=1, max_value=10,
                                         value=int(user.get("year_of_study") or 1))
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
        role = st.selectbox("Role", VALID_ROLES,
                             index=VALID_ROLES.index(user.get("role","student"))
                             if user.get("role") in VALID_ROLES else 2)
        submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if submitted:
        fn = full_name_val.strip()
        parts = fn.split(" ", 1)
        return {
            "full_name":       fn,
            "first_name":      parts[0] if parts else fn,
            "last_name":       parts[1] if len(parts) > 1 else "",
            "enrollment_number": enrollment_no.strip(), "student_id": enrollment_no.strip(),
            "program": program.strip(), "year_of_study": year_of_study,
            "date_of_birth": str(dob) if dob else None,
            "phone": phone.strip(), "address": address.strip(), "role": role,
        }
    return None


def _reset_password_form(user: dict) -> None:
    uid   = user["id"]
    email = user.get("email","")
    with st.form(f"reset_form_{uid}"):
        new_pass     = st.text_input("New Password",     type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        c1, c2 = st.columns(2)
        save   = c1.form_submit_button("🔑 Reset Password", use_container_width=True)
        cancel = c2.form_submit_button("Cancel",            use_container_width=True)

    if cancel:
        del st.session_state[f"resetting_{uid}"]
        st.rerun()

    if save:
        if not new_pass or not confirm_pass:
            st.error("Both fields are required.")
        elif len(new_pass) < 8:
            st.error("Password must be at least 8 characters.")
        elif new_pass != confirm_pass:
            st.error("Passwords do not match.")
        else:
            try:
                supabase.auth.admin.update_user_by_id(uid, {"password": new_pass})
                supabase.table("profiles")\
                    .update({"force_password_change": True})\
                    .eq("id", uid).execute()
                AdminService.clear_cache()
                st.success(f"Password reset. User will be prompted to change it on next login.")
                del st.session_state[f"resetting_{uid}"]
                st.rerun()
            except Exception as e:
                logger.exception(f"Password reset failed for {email}")
                st.error("Reset failed. Please try again.")


def _render_user_card(user: dict, role_type: str) -> None:
    uid          = user["id"]
    name         = _full_name(user)
    email        = user.get("email", "—")
    approved     = user.get("approved", False)
    edit_key     = f"editing_{uid}"
    reset_key    = f"resetting_{uid}"
    status_icon  = "✅" if approved else "⏳"

    with st.expander(f"{status_icon} **{name}** — {email}"):

        # ── VIEW mode ──────────────────────────────────────────────
        if not st.session_state.get(edit_key) and not st.session_state.get(reset_key):
            if role_type == "faculty":
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Employee ID:** {user.get('employee_id','—') or '—'}")
                c2.markdown(f"**Phone:** {user.get('phone','—') or '—'}")
                c3.markdown(f"**Office:** {user.get('office_location','—') or '—'}")
                c1.markdown(f"**Qualification:** {user.get('qualification','—') or '—'}")
                c2.markdown(f"**Specialization:** {user.get('specialization','—') or '—'}")
                c3.markdown(f"**Approved:** {'Yes ✅' if approved else 'No ⏳'}")
                if user.get("address"):
                    st.markdown(f"**Address:** {user['address']}")
                if user.get("publications"):
                    st.markdown(f"**Publications:** {user['publications']}")
            else:
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Full Name:** {_full_name(user)}")
                c2.markdown(f"**Enrollment No:** {user.get('enrollment_number','—') or '—'}")
                c3.markdown(f"**Program:** {user.get('program','—') or '—'}")
                c1.markdown(f"**Phone:** {user.get('phone','—') or '—'}")
                c2.markdown(f"**Year:** {user.get('year_of_study','—') or '—'}")
                c3.markdown(f"**DOB:** {user.get('date_of_birth','—') or '—'}")
                if user.get("address"):
                    st.markdown(f"**Address:** {user['address']}")

            st.divider()
            is_ultra  = user.get("role") == "faculty_ultra"
            col_edit, col_reset, col_ultra, col_del = st.columns(4)

            if col_ultra.button(
                "⬇️ Downgrade" if is_ultra else "⬆️ Ultra",
                key=f"ultra_btn_{uid}", use_container_width=True,
                help="Toggle Faculty Ultra status",
            ):
                new_role = "faculty" if is_ultra else "faculty_ultra"
                from services.admin_service import AdminService
                if AdminService.update_profile(uid, {"role": new_role}):
                    st.success(f"Role updated to {new_role}.")
                    st.rerun()

            if col_edit.button("✏️ Edit", key=f"edit_btn_{uid}", use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()
            if col_reset.button("🔑 Reset Password", key=f"reset_btn_{uid}",
                                  use_container_width=True):
                st.session_state[reset_key] = True
                st.rerun()
            if col_del.button("🗑️ Delete", key=f"del_btn_{uid}",
                               use_container_width=True, type="secondary"):
                st.session_state[f"confirm_delete_{uid}"] = True

            if st.session_state.get(f"confirm_delete_{uid}"):
                st.warning(f"⚠️ Permanently delete **{name}**?")
                y, n = st.columns(2)
                if y.button("Yes, Delete", key=f"confirm_yes_{uid}",
                             type="primary", use_container_width=True):
                    if AdminService.delete_user(uid):
                        st.success("User deleted.")
                        del st.session_state[f"confirm_delete_{uid}"]
                        st.rerun()
                    else:
                        st.error("Delete failed.")
                if n.button("Cancel", key=f"confirm_no_{uid}", use_container_width=True):
                    del st.session_state[f"confirm_delete_{uid}"]
                    st.rerun()

        # ── EDIT mode ──────────────────────────────────────────────
        elif st.session_state.get(edit_key):
            if role_type == "faculty":
                data = _faculty_edit_form(user, f"edit_form_{uid}")
            else:
                data = _student_edit_form(user, f"edit_form_{uid}")

            if data is not None:
                with st.spinner("Saving changes..."):
                    ok = AdminService.update_profile(uid, data)
                if ok:
                    st.success("✅ Profile updated successfully.")
                    del st.session_state[edit_key]
                    st.rerun()
                else:
                    st.error("❌ Save failed. Please try again.")

            if st.button("← Cancel", key=f"cancel_edit_{uid}"):
                del st.session_state[edit_key]
                st.rerun()

        # ── RESET PASSWORD mode ────────────────────────────────────
        elif st.session_state.get(reset_key):
            st.markdown(f"**Reset password for:** {email}")
            _reset_password_form(user)


# ================================================================
# BULK STUDENT UPLOAD
# ================================================================

def _render_bulk_upload() -> None:
    render_bulk_enrollment(domain_default="um.ar", allowed_course_ids=None, role="admin")


# ================================================================
# ENROLLMENT MANAGEMENT
# ================================================================

def _render_enrollment_management() -> None:
    st.title("📋 Course Enrollment")

    sems    = SemesterService.get_all()
    courses = CourseService.get_all()

    if not sems or not courses:
        st.warning("Please create semesters and courses first.")
        return

    sem_map    = {s["name"]: s["id"] for s in sems}
    active_sem = SemesterService.get_active()
    sem_names  = list(sem_map.keys())
    default    = active_sem["name"] if active_sem and active_sem["name"] in sem_names else sem_names[0]

    sel_sem_name = st.selectbox("Semester", sem_names,
                                 index=sem_names.index(default), key="enroll_sem")
    sel_sem_id   = sem_map[sel_sem_name]
    sem_courses  = [c for c in courses if c.get("semester_id") == sel_sem_id]

    if not sem_courses:
        st.info("No courses for this semester.")
        return

    course_map       = {f"{c['code']} — {c['name']}": c for c in sem_courses}
    sel_course_label = st.selectbox("Course", list(course_map.keys()), key="enroll_course")
    sel_course       = course_map[sel_course_label]
    course_id        = sel_course["id"]

    tab_enrolled, tab_add = st.tabs(["📋 Enrolled Students", "➕ Add Student"])

    with tab_enrolled:
        enrollments = EnrollmentService.get_course_enrollments(course_id)
        if not enrollments:
            st.info("No students enrolled yet.")
        else:
            section_header("Enrolled Students", f"{len(enrollments)} student(s)")
            for e in enrollments:
                p = e.get("profiles", {}) or {}
                c1, c2, c3, c4 = st.columns([3,2,2,1])
                c1.write(f"**{_full_name(p)}**")
                c2.write(p.get("enrollment_number","—"))
                c3.write(p.get("program","—"))
                if c4.button("Drop", key=f"drop_{e['id']}"):
                    if EnrollmentService.drop_student(p["id"], course_id, sel_sem_id):
                        st.success("Student dropped.")
                        st.rerun()
                st.divider()

    with tab_add:
        all_students = AdminService.get_student_users()
        enrolled_ids = {
            e["profiles"]["id"]
            for e in EnrollmentService.get_course_enrollments(course_id)
            if e.get("profiles")
        }
        available = [s for s in all_students if s["id"] not in enrolled_ids]
        if not available:
            st.info("All students are already enrolled.")
        else:
            student_map = {
                f"{_full_name(s)} — {s.get('enrollment_number','') or s['email']}": s["id"]
                for s in available
            }
            sel_label = st.selectbox("Select Student", list(student_map.keys()))
            if st.button("➕ Enroll Student", use_container_width=True):
                if EnrollmentService.enroll_student(
                    student_map[sel_label], course_id, sel_sem_id
                ):
                    st.success("Enrolled.")
                    st.rerun()
                else:
                    st.error("Enrollment failed.")


def _render_admin_upro() -> None:
    """Admin UPro Grade — access any course."""
    st.title("🏆 UPro Grade — Admin")
    sems = SemesterService.get_all()
    if not sems:
        st.warning("No semesters found.")
        return
    sem_map    = {s["name"]: s["id"] for s in sems}
    active_sem = SemesterService.get_active()
    sem_names  = list(sem_map.keys())
    default    = active_sem["name"] if active_sem and active_sem["name"] in sem_names else sem_names[0]
    sel_sem    = st.selectbox("Semester", sem_names,
                               index=sem_names.index(default), key="adm_upro_sem")
    sel_sem_id = sem_map[sel_sem]
    from services.course_service import CourseService
    courses = CourseService.get_all(sel_sem_id)
    if not courses:
        st.info("No courses for this semester.")
        return
    course_opts = {
        f"{c['code']} — {c['name']} [{c.get('course_id','—')}]": c
        for c in courses
    }
    sel_label   = st.selectbox("Course", list(course_opts.keys()), key="adm_upro_course")
    course      = course_opts[sel_label]
    course_uuid = course["id"]
    course_info = {
        "code":      course.get("code",""),
        "name":      course.get("name",""),
        "course_id": course.get("course_id",""),
        "semester":  sel_sem,
    }
    st.divider()
    render_upro_grade(course_uuid, course_info, is_admin=True)


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
            "📋 Enrollment",
            "📋 Bulk Enrollment",
            "📒 Gradebook",
            "🏆 UPro Grade",
            "📈 Reports",
            "📣 Communications",
            "👨‍🏫 Faculty",
            "🎓 Students",
            "✅ Pending Approvals",
            "🔒 Change Password",
        ]
    )

    if   menu == "📊 Dashboard":        _render_dashboard()
    elif menu == "🏛️ Departments":      _render_departments()
    elif menu == "📅 Semesters":        _render_semesters()
    elif menu == "📚 Courses":          _render_courses()
    elif menu == "📋 Enrollment":       _render_enrollment_management()
    elif menu == "📋 Bulk Enrollment":      _render_bulk_upload()
    elif menu == "📒 Gradebook":          render_admin_gradebook()
    elif menu == "🏆 UPro Grade":
        _render_admin_upro()
    elif menu == "📈 Reports":            render_admin_reports()
    elif menu == "📣 Communications":     render_admin_communications(st.session_state.user.id)
    elif menu == "👨‍🏫 Faculty":          _render_users("faculty")
    elif menu == "🎓 Students":         _render_users("student")
    elif menu == "✅ Pending Approvals": _render_pending_approvals()
    elif menu == "🔒 Change Password":
        st.title("🔒 Change Password")
        st.divider()
        render_change_password()


# ================================================================
# PAGE RENDERERS
# ================================================================

def _render_dashboard() -> None:
    st.title("Admin Dashboard")
    metrics    = AdminService.get_system_metrics()
    active_sem = SemesterService.get_active()

    if active_sem:
        st.info(f"📅 Active Semester: **{active_sem['name']}**  "
                f"({active_sem['start_date']} → {active_sem['end_date']})")
    else:
        st.warning("⚠️ No active semester set. Go to Semesters to activate one.")

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Users", metrics["total_users"])
    c2.metric("Faculty",     metrics["faculty"])
    c3.metric("Students",    metrics["students"])
    c4.metric("Admins",      metrics["admins"])

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        section_header("Departments")
        depts = DepartmentService.get_all()
        if depts:
            st.dataframe(
                [{"Department": d["name"], "Campus": d.get("campus","—"),
                  "School": d.get("school","—"), "HoD": d.get("hod_name","—")}
                 for d in depts],
                use_container_width=True, hide_index=True)
        else:
            st.info("No departments yet.")
    with col_b:
        section_header("Semesters")
        sems = SemesterService.get_all()
        if sems:
            st.dataframe(
                [{"Name": s["name"], "Start": s["start_date"],
                  "End": s["end_date"], "Active": "✅" if s["is_active"] else "—"}
                 for s in sems],
                use_container_width=True, hide_index=True)
        else:
            st.info("No semesters yet.")


def _render_departments() -> None:
    st.title("🏛️ Departments")
    with st.expander("➕ Add New Department", expanded=False):
        with st.form("add_dept_form"):
            c1, c2      = st.columns(2)
            d_campus    = c1.text_input("Campus",     placeholder="e.g. Main Campus")
            d_school    = c2.text_input("School",     placeholder="e.g. School of Engineering")
            d_dept      = st.text_input("Department", placeholder="e.g. Computer Science")
            c3, c4      = st.columns(2)
            d_hod_name  = c3.text_input("HoD Name",  placeholder="e.g. Dr. John Smith")
            d_hod_email = c4.text_input("HoD Email", placeholder="e.g. j.smith@university.edu")
            if st.form_submit_button("Create Department", use_container_width=True):
                if not d_dept or not d_campus:
                    st.warning("Campus and Department are required.")
                elif DepartmentService.create({
                    "name": d_dept, "campus": d_campus, "school": d_school,
                    "department": d_dept, "hod_name": d_hod_name, "hod_email": d_hod_email,
                }):
                    st.success(f"Department '{d_dept}' created.")
                    st.rerun()
                else:
                    st.error("Failed to create department.")

    st.divider()
    depts = DepartmentService.get_all()
    if not depts:
        st.info("No departments found.")
        return
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
            if col_e.button("✏️ Edit",   key=f"edit_dept_{dept['id']}", use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()
            if col_d.button("🗑️ Delete", key=f"del_dept_{dept['id']}",
                             use_container_width=True, type="secondary"):
                if DepartmentService.delete(dept["id"]):
                    st.success("Deleted.")
                    st.rerun()
            if st.session_state.get(edit_key):
                with st.form(f"edit_dept_form_{dept['id']}"):
                    c1, c2        = st.columns(2)
                    new_campus    = c1.text_input("Campus",     value=dept.get("campus",""))
                    new_school    = c2.text_input("School",     value=dept.get("school",""))
                    new_dept      = st.text_input("Department", value=dept.get("department",""))
                    c3, c4        = st.columns(2)
                    new_hod_name  = c3.text_input("HoD Name",  value=dept.get("hod_name",""))
                    new_hod_email = c4.text_input("HoD Email", value=dept.get("hod_email",""))
                    s1, s2 = st.columns(2)
                    if s1.form_submit_button("Save", use_container_width=True):
                        if DepartmentService.update(dept["id"], {
                            "name": new_dept, "campus": new_campus, "school": new_school,
                            "department": new_dept, "hod_name": new_hod_name,
                            "hod_email": new_hod_email,
                        }):
                            del st.session_state[edit_key]
                            st.success("Updated.")
                            st.rerun()
                        else:
                            st.error("Update failed.")
                    if s2.form_submit_button("Cancel", use_container_width=True):
                        del st.session_state[edit_key]
                        st.rerun()


def _render_semesters() -> None:
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
                elif SemesterService.create(sem_name, str(start), str(end)):
                    st.success(f"Semester '{sem_name}' created.")
                    st.rerun()
                else:
                    st.error("Failed. Name may already exist.")

    st.divider()
    section_header("All Semesters")

    sems = SemesterService.get_all()
    if not sems:
        st.info("No semesters yet.")
        return

    for sem in sems:
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
            c1.write(f"**{sem['name']}**")
            c2.write(f"📅 {sem['start_date']}")
            c3.write(f"📅 {sem['end_date']}")

            if sem["is_active"]:
                c4.markdown("✅ **Active**")
            else:
                if c4.button("▶ Activate", key=f"act_sem_{sem['id']}",
                              use_container_width=True, type="primary"):
                    with st.spinner("Activating..."):
                        ok = SemesterService.set_active(sem["id"])
                    if ok:
                        st.success(f"'{sem['name']}' is now the active semester.")
                        st.rerun()
                    else:
                        st.error("Activation failed. Check Supabase logs.")

            if not sem["is_active"]:
                if c5.button("🗑️", key=f"del_sem_{sem['id']}"):
                    SemesterService.delete(sem["id"])
                    st.rerun()
        st.divider()


def _render_courses() -> None:
    st.title("📚 Course Management")
    depts = DepartmentService.get_all()
    sems  = SemesterService.get_all()
    if not depts:
        st.warning("Please create at least one department first.")
        return
    if not sems:
        st.warning("Please create at least one semester first.")
        return

    dept_map    = {d["name"]: d["id"] for d in depts}
    sem_map     = {s["name"]: s["id"] for s in sems}
    active_sem  = SemesterService.get_active()
    sem_names   = list(sem_map.keys())
    default_sem = active_sem["name"] if active_sem and active_sem["name"] in sem_names else sem_names[0]

    sel_sem_name = st.selectbox("Filter by Semester", sem_names,
                                 index=sem_names.index(default_sem), key="course_sem_filter")
    sel_sem_id   = sem_map[sel_sem_name]

    with st.expander("➕ Add New Course", expanded=False):
        with st.form("add_course_form"):
            c1, c2 = st.columns(2)
            c_name = c1.text_input("Course Name", placeholder="e.g. Data Structures")
            c_code = c2.text_input("Course Code", placeholder="e.g. CS201")
            c3, c4 = st.columns(2)
            c_dept = c3.selectbox("Department", list(dept_map.keys()))
            c_sem  = c4.selectbox("Semester", sem_names, index=sem_names.index(sel_sem_name))
            c5, c6 = st.columns(2)
            c_credits  = c5.number_input("Credits",      min_value=1, max_value=6, value=3)
            c_max_stud = c6.number_input("Max Students", min_value=1, max_value=500, value=40)
            c_course_id_override = st.text_input(
                "Course ID (optional — leave blank to auto-generate)",
                placeholder="e.g. CS3X7K2",
                help="7-character alphanumeric. Auto-generated if left blank."
            )
            c_desc = st.text_area("Description (optional)", height=60)
            if st.form_submit_button("Create Course", use_container_width=True):
                if not c_name or not c_code:
                    st.warning("Course name and code are required.")
                elif c_course_id_override and len(c_course_id_override.strip()) != 7:
                    st.error("Course ID must be exactly 7 characters.")
                elif CourseService.create(c_name, c_code, dept_map[c_dept],
                                          sem_map[c_sem], c_credits, c_max_stud, c_desc,
                                          c_course_id_override):
                    st.success(f"Course '{c_code} — {c_name}' created.")
                    st.rerun()
                else:
                    st.error("Failed. Code may already exist.")

    st.divider()

    all_users    = AdminService.get_all_users()
    faculty_list = [u for u in all_users if u.get("role") == "faculty" and u.get("approved")]
    faculty_map  = {f"{_full_name(u)} ({u['email']})": u["id"] for u in faculty_list}

    courses = CourseService.get_all(sel_sem_id)
    section_header(f"Courses — {sel_sem_name}", f"{len(courses)} course(s)")

    if not courses:
        st.info("No courses for this semester.")
        return

    for course in courses:
        dept_name = (course.get("departments") or {}).get("name", "—")
        enrolled  = CourseService.get_enrollment_count(course["id"])
        with st.expander(
            f"📘 **{course['code']}** — {course['name']}  "
            f"| ID: `{course.get('course_id','—')}` "
            f"| {dept_name} | {course['credits']} cr "
            f"| {enrolled}/{course['max_students']} enrolled"
        ):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Course ID:** `{course.get('course_id','—')}`")
            c2.markdown(f"**Description:** {course.get('description') or '—'}")
            c3.markdown(f"**Max Students:** {course['max_students']}")

            st.markdown("**👨‍🏫 Assigned Faculty:**")
            assigned = CourseService.get_assigned_faculty(course["id"])
            if assigned:
                for a in assigned:
                    p = a.get("profiles", {}) or {}
                    ca, cb = st.columns([5, 1])
                    ca.write(f"👨‍🏫 {_full_name(p) if p else '—'}")
                    if cb.button("Remove", key=f"unassign_{course['id']}_{a['faculty_id']}"):
                        CourseService.unassign_faculty(course["id"], a["faculty_id"])
                        st.rerun()
            else:
                st.caption("No faculty assigned yet.")

            if faculty_map:
                with st.form(f"assign_form_{course['id']}"):
                    sel_f = st.selectbox("Assign Faculty", list(faculty_map.keys()),
                                          key=f"sel_fac_{course['id']}")
                    if st.form_submit_button("Assign Faculty", use_container_width=True):
                        if CourseService.assign_faculty(course["id"], faculty_map[sel_f]):
                            st.success("Faculty assigned.")
                            st.rerun()
            else:
                st.caption("No approved faculty available.")

            st.divider()
            if st.button("🗑️ Delete Course", key=f"del_course_{course['id']}",
                          type="secondary"):
                if CourseService.delete(course["id"]):
                    st.success("Deleted.")
                    st.rerun()


def _render_users(role_type: str) -> None:
    title = "👨‍🏫 Faculty Management" if role_type == "faculty" else "🎓 Student Management"
    st.title(title)

    users = AdminService.get_faculty_users() if role_type == "faculty" \
            else AdminService.get_student_users()

    if not users:
        st.info(f"No {role_type}s registered yet.")
        return

    search = st.text_input(
        "🔍 Search by name, email" + (", or enrollment number" if role_type == "student" else ""),
        placeholder="Type to filter...", key=f"{role_type}_search"
    )
    if search:
        q = search.lower()
        users = [
            u for u in users
            if q in u.get("email","").lower()
            or q in _full_name(u).lower()
            or (role_type == "student" and
                q in (u.get("enrollment_number","") or "").lower())
        ]

    if role_type == "faculty":
        approved_users = [u for u in users if u.get("approved")]
        pending_users  = [u for u in users if not u.get("approved")]
        st.caption(f"{len(users)} total · {len(approved_users)} approved · {len(pending_users)} pending")
        st.divider()
        if pending_users:
            section_header("⏳ Pending Approval", f"{len(pending_users)} awaiting")
            for u in pending_users:
                _render_user_card(u, "faculty")
            st.divider()
        if approved_users:
            section_header("✅ Active Faculty", f"{len(approved_users)} members")
            for u in approved_users:
                _render_user_card(u, "faculty")
    else:
        st.caption(f"{len(users)} student(s)")
        st.divider()
        for u in users:
            _render_user_card(u, "student")


def _render_pending_approvals() -> None:
    st.title("✅ Faculty Pending Approval")
    pending = AdminService.get_pending_faculty()
    if not pending:
        st.success("No pending approvals at this time.")
        return
    for user in pending:
        with st.container():
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.write(f"📧 **{user.get('email','—')}**  "
                     f"| {_full_name(user) or '—'}")
            if c2.button("✅ Approve", key=f"approve_{user['id']}"):
                if AdminService.approve_faculty(user["id"]):
                    st.success("Approved.")
                    st.rerun()
            if c3.button("❌ Reject", key=f"reject_{user['id']}"):
                if AdminService.reject_faculty(user["id"]):
                    st.warning("Rejected.")
                    st.rerun()
        st.divider()
