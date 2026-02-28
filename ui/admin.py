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
            "🎓 Academic Ops",
            "👥 User Control",
            "📒 Gradebook",
            "🏆 UPro Grade",
            "📈 Reports",
            "📣 Communications",
            "🔒 Change Password",
        ]
    )

    if   menu == "📊 Dashboard":         _render_dashboard()
    elif menu == "🎓 Academic Ops":       _render_academic_ops_hub()
    elif menu == "👥 User Control":       _render_user_control_hub()
    elif menu == "📒 Gradebook":          render_admin_gradebook()
    elif menu == "🏆 UPro Grade":         _render_admin_upro()
    elif menu == "📈 Reports":            render_admin_reports()
    elif menu == "📣 Communications":     render_admin_communications(st.session_state.user.id)
    elif menu == "🔒 Change Password":
        st.title("🔒 Change Password")
        st.divider()
        render_change_password()


# ================================================================
# SUB-PAGE ROUTER
# ================================================================

def _route_subpage() -> None:
    """Render the current subpage. Does NOT clear state — caller manages that."""
    sub = st.session_state.get("_subpage")
    if not sub:
        return

    # Back button at top
    if st.button("← Back", key="subpage_back"):
        st.session_state["_subpage"] = None
        st.rerun()

    dispatch = {
        "departments":     _render_departments,
        "semesters":       _render_semesters,
        "courses":         _render_courses,
        "faculty":         lambda: _render_users("faculty"),
        "faculty_ultra":   _render_faculty_ultra_users,
        "students":        lambda: _render_users("student"),
        "pending":         _render_pending_approvals,
        "enrollment":      _render_enrollment_management,
        "bulk_enrollment": _render_bulk_upload,
        "add_new_user":    _render_add_new_user,
    }
    fn = dispatch.get(sub)
    if fn:
        fn()
    else:
        st.session_state["_subpage"] = None
        st.rerun()


# ================================================================
# HUB PAGES
# ================================================================

def _hub_tile(col, icon: str, label: str, subpage: str, count: str = "") -> None:
    col.markdown(f"""
    <div style="background:#ffffff;border:1.5px solid #e8f0f2;border-radius:14px;
                padding:1.4rem 1rem 0.6rem;text-align:center;
                box-shadow:0 2px 10px rgba(48,120,144,0.08);margin-bottom:0.2rem;">
        <div style="font-size:2.2rem;margin-bottom:0.35rem;">{icon}</div>
        <div style="font-size:0.92rem;font-weight:700;color:#186078;">{label}</div>
        {f'<div style="font-size:0.76rem;color:#64748b;margin-top:3px;">{count}</div>' if count else ''}
    </div>
    """, unsafe_allow_html=True)
    if col.button(f"Open {label}", key=f"hub_{subpage}", use_container_width=True):
        st.session_state["_subpage"] = subpage
        st.rerun()


def _render_academic_ops_hub() -> None:
    # If a non-academic subpage is active, clear it (came from other hub)
    _academic_subs = {"departments", "semesters", "courses"}
    if st.session_state.get("_subpage") and        st.session_state["_subpage"] not in _academic_subs:
        st.session_state["_subpage"] = None
    if st.session_state.get("_subpage"):
        _route_subpage()
        return

    from ui.styles import page_header
    page_header("🎓", "Academic Ops", "Manage departments, semesters and courses")

    try:
        dept_count   = len(DepartmentService.get_all())
        sem_count    = len(SemesterService.get_all())
        course_count = len(CourseService.get_all())
    except Exception:
        dept_count = sem_count = course_count = 0

    c1, c2, c3 = st.columns(3)
    _hub_tile(c1, "🏛️", "Departments", "departments", f"{dept_count} department(s)")
    _hub_tile(c2, "📅", "Semesters",   "semesters",   f"{sem_count} semester(s)")
    _hub_tile(c3, "📚", "Courses",     "courses",     f"{course_count} course(s)")


def _render_user_control_hub() -> None:
    # If a non-user-control subpage is active, clear it (came from other hub)
    _user_subs = {"faculty", "faculty_ultra", "students", "pending", "enrollment", "bulk_enrollment", "add_new_user"}
    if st.session_state.get("_subpage") and        st.session_state["_subpage"] not in _user_subs:
        st.session_state["_subpage"] = None
    if st.session_state.get("_subpage"):
        _route_subpage()
        return

    from ui.styles import page_header
    page_header("👥", "User Control", "Manage faculty, students, enrollment and approvals")

    try:
        all_users  = AdminService.get_all_users()
        fac_count  = sum(1 for u in all_users if u.get("role") == "faculty")
        stu_count  = sum(1 for u in all_users if u.get("role") == "student")
        pend_count = sum(1 for u in all_users if not u.get("approved"))
    except Exception:
        fac_count = stu_count = pend_count = 0

    try:
        ultra_count = sum(1 for u in all_users if u.get("role") == "faculty_ultra")
    except Exception:
        ultra_count = 0

    c1, c2, c3 = st.columns(3)
    _hub_tile(c1, "👨‍🏫", "Faculty",          "faculty",       f"{fac_count} member(s)")
    _hub_tile(c2, "⭐",  "Faculty Ultra",     "faculty_ultra", f"{ultra_count} member(s)")
    _hub_tile(c3, "🎓",  "Students",          "students",      f"{stu_count} student(s)")
    st.markdown("<br>", unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    _hub_tile(c4, "✅",  "Pending Approvals", "pending",       f"{pend_count} pending")
    _hub_tile(c5, "📋",  "Enrollment",        "enrollment")
    _hub_tile(c6, "📤",  "Bulk Enrollment",   "bulk_enrollment")
    st.markdown("<br>", unsafe_allow_html=True)
    c7, c8, c9 = st.columns(3)
    _hub_tile(c7, "➕",  "Add New User",      "add_new_user")


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
        with st.expander(
            f"{'✅' if sem['is_active'] else '📅'} **{sem['name']}**  "
            f"·  {sem['start_date']} → {sem['end_date']}"
            f"{'  · 🟢 Active' if sem['is_active'] else ''}",
            expanded=False,
        ):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Name:** {sem['name']}")
            c2.markdown(f"**Start:** {sem['start_date']}")
            c3.markdown(f"**End:** {sem['end_date']}")

            # Action buttons row
            btn_cols = st.columns(4)

            # Activate
            if sem["is_active"]:
                btn_cols[0].success("✅ Active")
            else:
                if btn_cols[0].button("▶️ Activate", key=f"act_sem_{sem['id']}",
                                       use_container_width=True):
                    if SemesterService.set_active(sem["id"]):
                        st.success(f"'{sem['name']}' activated.")
                        st.rerun()
                    else:
                        st.error("Activation failed.")

            # Edit
            if btn_cols[1].button("✏️ Edit", key=f"edit_sem_btn_{sem['id']}",
                                   use_container_width=True):
                st.session_state[f"_edit_sem_{sem['id']}"] = True

            # Delete (only inactive)
            if not sem["is_active"]:
                if btn_cols[2].button("🗑️ Delete", key=f"del_sem_{sem['id']}",
                                       use_container_width=True):
                    SemesterService.delete(sem["id"])
                    st.rerun()
            else:
                btn_cols[2].caption("Cannot delete active")

            # Inline edit form
            if st.session_state.get(f"_edit_sem_{sem['id']}"):
                st.divider()
                with st.form(f"edit_sem_form_{sem['id']}"):
                    st.markdown("**✏️ Edit Semester**")
                    new_name  = st.text_input("Semester Name", value=sem["name"])
                    ec1, ec2  = st.columns(2)
                    from datetime import date
                    new_start = ec1.date_input("Start Date",
                                               value=date.fromisoformat(sem["start_date"]),
                                               key=f"sem_start_{sem['id']}")
                    new_end   = ec2.date_input("End Date",
                                               value=date.fromisoformat(sem["end_date"]),
                                               key=f"sem_end_{sem['id']}")
                    fc1, fc2  = st.columns(2)
                    save   = fc1.form_submit_button("💾 Save",   use_container_width=True)
                    cancel = fc2.form_submit_button("✖ Cancel", use_container_width=True)
                if save:
                    if not new_name:
                        st.error("Name is required.")
                    elif new_end <= new_start:
                        st.error("End must be after start.")
                    else:
                        SemesterService.update(sem["id"], {
                            "name":       new_name,
                            "start_date": str(new_start),
                            "end_date":   str(new_end),
                        })
                        st.session_state.pop(f"_edit_sem_{sem['id']}", None)
                        st.rerun()
                if cancel:
                    st.session_state.pop(f"_edit_sem_{sem['id']}", None)
                    st.rerun()


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
        dept_name  = (course.get("departments") or {}).get("name", "—")
        enrolled   = CourseService.get_enrollment_count(course["id"])
        is_active  = course.get("is_active", True)
        status_tag = "🟢" if is_active else "🔴"

        with st.expander(
            f"{status_tag} 📘 **{course['code']}** — {course['name']}  "
            f"| ID: `{course.get('course_id','—')}` "
            f"| {dept_name} | {course['credits']} cr "
            f"| {enrolled}/{course['max_students']} enrolled"
        ):
            # ── Sub-tabs inside each course ──────────────────────
            ctab_info, ctab_faculty, ctab_enroll, ctab_bulk = st.tabs([
                "📋 Info & Actions",
                "👨‍🏫 Faculty",
                "📋 Enrollment",
                "📤 Bulk Enrollment",
            ])

            with ctab_info:
                ci1, ci2, ci3 = st.columns(3)
                ci1.markdown(f"**Course ID:** `{course.get('course_id','—')}`")
                ci2.markdown(f"**Credits:** {course['credits']}")
                ci3.markdown(f"**Max Students:** {course['max_students']}")
                if course.get("description"):
                    st.caption(course["description"])

                st.markdown("---")
                ba, bb, bc = st.columns(3)

                # Deactivate / Activate
                deact_lbl = "🔴 Deactivate" if is_active else "🟢 Activate"
                if ba.button(deact_lbl, key=f"deact_course_{course['id']}",
                              use_container_width=True):
                    CourseService.update(course["id"], {"is_active": not is_active})
                    st.rerun()

                # Edit
                if bb.button("✏️ Edit", key=f"edit_course_btn_{course['id']}",
                              use_container_width=True):
                    st.session_state[f"_edit_course_{course['id']}"] = True

                # Delete
                if bc.button("🗑️ Delete", key=f"del_course_{course['id']}",
                              use_container_width=True):
                    if CourseService.delete(course["id"]):
                        st.success("Deleted.")
                        st.rerun()

                # Inline edit form
                if st.session_state.get(f"_edit_course_{course['id']}"):
                    st.divider()
                    with st.form(f"edit_course_form_{course['id']}"):
                        st.markdown("**✏️ Edit Course**")
                        en1, en2 = st.columns(2)
                        new_name = en1.text_input("Course Name", value=course["name"])
                        new_code = en2.text_input("Course Code", value=course["code"])
                        en3, en4 = st.columns(2)
                        new_cred = en3.number_input("Credits", min_value=1, max_value=6,
                                                     value=int(course["credits"]),
                                                     key=f"cr_{course['id']}")
                        new_max  = en4.number_input("Max Students", min_value=1, max_value=500,
                                                     value=int(course["max_students"]),
                                                     key=f"mx_{course['id']}")
                        new_dept_name = st.selectbox("Department", list(dept_map.keys()),
                                                      index=list(dept_map.keys()).index(
                                                          (course.get("departments") or {}).get("name", list(dept_map.keys())[0])
                                                      ) if (course.get("departments") or {}).get("name") in dept_map else 0,
                                                      key=f"dp_{course['id']}")
                        new_desc = st.text_area("Description", value=course.get("description",""),
                                                 height=60, key=f"ds_{course['id']}")
                        fc1, fc2 = st.columns(2)
                        save   = fc1.form_submit_button("💾 Save",   use_container_width=True)
                        cancel = fc2.form_submit_button("✖ Cancel", use_container_width=True)
                    if save:
                        CourseService.update(course["id"], {
                            "name":          new_name,
                            "code":          new_code.upper(),
                            "credits":       new_cred,
                            "max_students":  new_max,
                            "department_id": dept_map[new_dept_name],
                            "description":   new_desc,
                        })
                        st.session_state.pop(f"_edit_course_{course['id']}", None)
                        st.rerun()
                    if cancel:
                        st.session_state.pop(f"_edit_course_{course['id']}", None)
                        st.rerun()

            with ctab_faculty:
                st.markdown("**👨‍🏫 Assigned Faculty**")
                assigned = CourseService.get_assigned_faculty(course["id"])
                if assigned:
                    for a in assigned:
                        p = a.get("profiles", {}) or {}
                        fa, fb = st.columns([5, 1])
                        fa.write(f"👨‍🏫 {_full_name(p) if p else '—'}")
                        if fb.button("Remove", key=f"unassign_{course['id']}_{a['faculty_id']}"):
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

            with ctab_enroll:
                _render_course_inline_enrollment(course["id"], course["name"], sel_sem_id)

            with ctab_bulk:
                _render_course_inline_bulk(course["id"], course["name"])


def _render_course_inline_enrollment(course_id: str, course_name: str,
                                      sem_id: str) -> None:
    """Mini enrollment panel embedded inside a course expander tab."""
    tab_list, tab_add = st.tabs(["📋 Enrolled Students", "➕ Add Student"])

    with tab_list:
        enrollments = EnrollmentService.get_course_enrollments(course_id)
        if not enrollments:
            st.info("No students enrolled yet.")
        else:
            section_header("Enrolled Students", f"{len(enrollments)} student(s)")
            for e in enrollments:
                p  = e.get("profiles", {}) or {}
                ea, eb = st.columns([6, 1])
                name = p.get("full_name") or f"{p.get('first_name','')} {p.get('last_name','')}".strip() or "—"
                ea.write(f"🎓 {name} ({p.get('email','—')})")
                if eb.button("Drop", key=f"drop_{course_id}_{p.get('id','')}"):
                    if EnrollmentService.drop_student(p["id"], course_id, sem_id):
                        st.success("Student dropped.")
                        st.rerun()

    with tab_add:
        all_students = [u for u in AdminService.get_all_users()
                        if u.get("role") == "student"]
        already_ids  = {e.get("student_id") or (e.get("profiles") or {}).get("id")
                        for e in EnrollmentService.get_course_enrollments(course_id)}
        available    = [u for u in all_students if u["id"] not in already_ids]
        if not available:
            st.info("All students are already enrolled.")
        else:
            student_map = {
                f"{u.get('full_name') or (u.get('first_name','') + ' ' + u.get('last_name','')).strip()} ({u['email']})": u["id"]
                for u in available
            }
            sel_label = st.selectbox("Select Student", list(student_map.keys()),
                                      key=f"inline_enroll_sel_{course_id}")
            if st.button("➕ Enroll Student", key=f"inline_enroll_btn_{course_id}",
                          use_container_width=True):
                if EnrollmentService.enroll_student(
                    student_map[sel_label], course_id, sem_id
                ):
                    st.success("Student enrolled.")
                    st.rerun()
                else:
                    st.error("Enrollment failed.")


def _render_course_inline_bulk(course_id: str, course_name: str) -> None:
    """Mini bulk enrollment panel embedded inside a course expander tab."""
    st.markdown(f"**Bulk enroll students into {course_name}**")
    st.caption("Upload a CSV with columns: `student_id` or `email`")

    uploaded = st.file_uploader("Upload CSV", type=["csv"],
                                  key=f"bulk_upload_{course_id}")
    if uploaded:
        import io, csv
        try:
            text    = uploaded.read().decode("utf-8")
            reader  = csv.DictReader(io.StringIO(text))
            rows    = list(reader)
            headers = [h.lower().strip() for h in (reader.fieldnames or [])]
            st.info(f"Found {len(rows)} rows. Headers: {headers}")

            if st.button("⬆️ Process Bulk Enrollment",
                          key=f"bulk_process_{course_id}",
                          use_container_width=True):
                from services.supabase_client import supabase as _sb
                active_sem = SemesterService.get_active()
                sem_id     = active_sem["id"] if active_sem else None
                success = fail = 0
                for row in rows:
                    email = row.get("email","").strip()
                    if not email or not sem_id:
                        fail += 1
                        continue
                    r = _sb.table("profiles").select("id").eq("email", email).execute()
                    if not r.data:
                        fail += 1
                        continue
                    sid = r.data[0]["id"]
                    if EnrollmentService.enroll_student(sid, course_id, sem_id):
                        success += 1
                    else:
                        fail += 1
                st.success(f"✅ {success} enrolled, ❌ {fail} failed.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")


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


def _render_add_new_user() -> None:
    from ui.styles import page_header
    from services.auth_service import AuthService as _Auth

    page_header("➕", "Add New User", "Create a new admin, faculty, faculty ultra or student account")

    ROLES = {
        "👨‍🏫 Faculty":       "faculty",
        "⭐ Faculty Ultra":  "faculty_ultra",
        "🎓 Student":        "student",
        "🛡️ Admin":          "admin",
    }

    role_label = st.selectbox("User Role *", list(ROLES.keys()), key="new_user_role")
    role_val   = ROLES[role_label]

    with st.form("add_new_user_form", clear_on_submit=True):
        st.markdown(f"**Creating: {role_label}**")
        st.divider()

        # ── Credentials ──────────────────────────────────────────
        fc1, fc2 = st.columns(2)
        email    = fc1.text_input("Email Address *", placeholder="user@example.com")
        password = fc2.text_input("Password *", type="password",
                                   placeholder="Min 8 characters")

        # Initialise ALL variables first so they are never unbound
        full_name = first_name = last_name = employee_id = phone = ""
        auto_approve = True

        # ── Name fields ───────────────────────────────────────────
        if role_val == "student":
            full_name = st.text_input("Full Name *", placeholder="e.g. John Smith")
        else:
            fn1, fn2   = st.columns(2)
            first_name = fn1.text_input("First Name *", placeholder="e.g. John")
            last_name  = fn2.text_input("Last Name *",  placeholder="e.g. Smith")

        # ── Faculty-specific fields ───────────────────────────────
        if role_val in ("faculty", "faculty_ultra"):
            pf1, pf2    = st.columns(2)
            employee_id = pf1.text_input("Employee ID", placeholder="e.g. EMP001")
            phone       = pf2.text_input("Phone",       placeholder="e.g. +92 300 1234567")
            auto_approve = st.checkbox("Auto-approve (skip pending approval)",
                                        value=True, key="new_user_approve")

        st.divider()
        submitted = st.form_submit_button("➕ Create User", use_container_width=True)

    if submitted:
        errors = []
        if not email or "@" not in email:
            errors.append("Valid email is required.")
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if role_val == "student" and not full_name:
            errors.append("Full name is required for students.")
        if role_val != "student" and (not first_name or not last_name):
            errors.append("First and last name are required.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            ok, msg = _Auth.admin_create_user(
                email       = email.strip().lower(),
                password    = password,
                role        = role_val,
                first_name  = first_name.strip(),
                last_name   = last_name.strip(),
                full_name   = full_name.strip() if full_name else f"{first_name} {last_name}".strip(),
                employee_id = employee_id.strip(),
                phone       = phone.strip(),
                approved    = auto_approve,
            )
            if ok:
                st.success(f"✅ {msg}")
                st.balloons()
            else:
                st.error(f"❌ Failed: {msg}")


def _render_faculty_ultra_users() -> None:
    st.title("⭐ Faculty Ultra Management")

    all_users   = AdminService.get_all_users()
    ultra_users = [u for u in all_users if u.get("role") == "faculty_ultra"]

    search = st.text_input(
        "🔍 Search by name or email",
        placeholder="Type to filter...",
        key="faculty_ultra_search",
    )
    if search:
        q = search.lower()
        ultra_users = [
            u for u in ultra_users
            if q in u.get("email", "").lower() or q in _full_name(u).lower()
        ]

    if not ultra_users:
        st.info("No Faculty Ultra members found.")
        return

    st.caption(f"{len(ultra_users)} Faculty Ultra member(s)")
    st.divider()

    for user in ultra_users:
        uid   = user["id"]
        name  = _full_name(user)
        email = user.get("email", "—")

        with st.expander(f"⭐ **{name}** — {email}"):
            # Profile info
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Employee ID:** {user.get('employee_id','—') or '—'}")
            c2.markdown(f"**Phone:** {user.get('phone','—') or '—'}")
            c3.markdown(f"**Office:** {user.get('office_location','—') or '—'}")
            c1.markdown(f"**Qualification:** {user.get('qualification','—') or '—'}")
            c2.markdown(f"**Specialization:** {user.get('specialization','—') or '—'}")
            c3.markdown(f"**Approved:** {'Yes ✅' if user.get('approved') else 'No ⏳'}")
            if user.get("address"):
                st.markdown(f"**Address:** {user['address']}")
            if user.get("publications"):
                st.markdown(f"**Publications:** {user['publications']}")

            st.divider()

            col_edit, col_reset, col_down, col_del = st.columns(4)

            # ── Downgrade to Faculty ──────────────────────────────
            if col_down.button(
                "⬇️ Downgrade to Faculty",
                key=f"downgrade_{uid}",
                use_container_width=True,
                help="Remove Faculty Ultra status, revert to regular Faculty",
            ):
                if AdminService.update_profile(uid, {"role": "faculty"}):
                    st.success(f"{name} downgraded to Faculty.")
                    st.rerun()
                else:
                    st.error("Downgrade failed.")

            # ── Edit ──────────────────────────────────────────────
            edit_key = f"editing_{uid}"
            if col_edit.button("✏️ Edit", key=f"ultra_edit_btn_{uid}",
                                use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()

            # ── Reset Password ────────────────────────────────────
            reset_key = f"resetting_{uid}"
            if col_reset.button("🔑 Reset Password", key=f"ultra_reset_btn_{uid}",
                                 use_container_width=True):
                st.session_state[reset_key] = True
                st.rerun()

            # ── Delete ────────────────────────────────────────────
            if col_del.button("🗑️ Delete", key=f"ultra_del_btn_{uid}",
                               use_container_width=True):
                st.session_state[f"confirm_delete_{uid}"] = True

            if st.session_state.get(f"confirm_delete_{uid}"):
                st.warning(f"⚠️ Permanently delete **{name}**?")
                y, n = st.columns(2)
                if y.button("Yes, Delete", key=f"ultra_confirm_yes_{uid}",
                             use_container_width=True):
                    if AdminService.delete_user(uid):
                        st.success("User deleted.")
                        del st.session_state[f"confirm_delete_{uid}"]
                        st.rerun()
                    else:
                        st.error("Delete failed.")
                if n.button("Cancel", key=f"ultra_confirm_no_{uid}",
                             use_container_width=True):
                    del st.session_state[f"confirm_delete_{uid}"]
                    st.rerun()

            # ── Inline Edit Form ──────────────────────────────────
            if st.session_state.get(edit_key):
                st.divider()
                with st.form(f"ultra_edit_form_{uid}"):
                    st.markdown("**✏️ Edit Profile**")
                    ef1, ef2 = st.columns(2)
                    new_first = ef1.text_input("First Name", value=user.get("first_name",""))
                    new_last  = ef2.text_input("Last Name",  value=user.get("last_name",""))
                    ef3, ef4  = st.columns(2)
                    new_emp   = ef3.text_input("Employee ID",     value=user.get("employee_id","") or "")
                    new_phone = ef4.text_input("Phone",           value=user.get("phone","") or "")
                    ef5, ef6  = st.columns(2)
                    new_qual  = ef5.text_input("Qualification",   value=user.get("qualification","") or "")
                    new_spec  = ef6.text_input("Specialization",  value=user.get("specialization","") or "")
                    ef7, ef8  = st.columns(2)
                    new_off   = ef7.text_input("Office Location", value=user.get("office_location","") or "")
                    new_addr  = ef8.text_input("Address",         value=user.get("address","") or "")
                    new_pub   = st.text_area("Publications", value=user.get("publications","") or "", height=60)
                    fs1, fs2  = st.columns(2)
                    save   = fs1.form_submit_button("💾 Save",   use_container_width=True)
                    cancel = fs2.form_submit_button("✖ Cancel", use_container_width=True)
                if save:
                    AdminService.update_profile(uid, {
                        "first_name":       new_first,
                        "last_name":        new_last,
                        "employee_id":      new_emp,
                        "phone":            new_phone,
                        "qualification":    new_qual,
                        "specialization":   new_spec,
                        "office_location":  new_off,
                        "address":          new_addr,
                        "publications":     new_pub,
                    })
                    st.session_state.pop(edit_key, None)
                    st.rerun()
                if cancel:
                    st.session_state.pop(edit_key, None)
                    st.rerun()

            # ── Inline Reset Password Form ────────────────────────
            if st.session_state.get(reset_key):
                st.divider()
                with st.form(f"ultra_reset_form_{uid}"):
                    st.markdown("**🔑 Reset Password**")
                    new_pw  = st.text_input("New Password", type="password")
                    new_pw2 = st.text_input("Confirm Password", type="password")
                    rs1, rs2 = st.columns(2)
                    rsave   = rs1.form_submit_button("🔑 Reset",  use_container_width=True)
                    rcancel = rs2.form_submit_button("✖ Cancel", use_container_width=True)
                if rsave:
                    if not new_pw or new_pw != new_pw2:
                        st.error("Passwords must match and not be empty.")
                    else:
                        from services.auth_service import AuthService
                        ok, msg = AuthService.admin_reset_password(uid, new_pw)
                        if ok:
                            st.success("Password reset successfully.")
                            st.session_state.pop(reset_key, None)
                            st.rerun()
                        else:
                            st.error(f"Reset failed: {msg}")
                if rcancel:
                    st.session_state.pop(reset_key, None)
                    st.rerun()


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
