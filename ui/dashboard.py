import streamlit as st
from services.faculty_service import FacultyService
from services.student_service import StudentService
from services.course_service import CourseService
from services.semester_service import SemesterService
from ui.styles import section_header


def render_dashboard() -> None:
    role  = st.session_state.get("role")
    user  = st.session_state.get("user")

    if not user or not role:
        st.error("Session data is missing. Please log in again.")
        return

    if role == "faculty":
        data = FacultyService.get_profile(user.id)
    else:
        data = StudentService.get_profile(user.id)

    st.title("📊 Dashboard")

    if not data:
        st.warning("Profile data could not be loaded. Please contact support.")
        return

    # Students store name in full_name; faculty/admin use first_name + last_name
    full_name_field = (data.get("full_name") or "").strip()
    first = (data.get("first_name") or "").strip()
    last  = (data.get("last_name")  or "").strip()
    full_name = full_name_field or f"{first} {last}".strip() or user.email
    # Display name: prefer full_name, fall back to first name, then email
    display_first = full_name_field or first or full_name

    # Welcome banner
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
            border-radius: 16px;
            padding: 28px 32px;
            margin-bottom: 24px;
            color: white;
        ">
            <div style="font-size: 26px; font-weight: 700; margin-bottom: 4px;">
                Welcome back, {display_first}! 👋
            </div>
            <div style="font-size: 14px; color: #94a3b8;">
                {role.capitalize()} · {user.email}
            </div>
        </div>
    """, unsafe_allow_html=True)

    active_sem = SemesterService.get_active()

    # Role-specific dashboard content
    if role == "faculty":
        _faculty_dashboard(user, active_sem)
    elif role == "student":
        _student_dashboard(user, active_sem)
    elif role == "admin":
        from services.admin_service import AdminService
        metrics = AdminService.get_system_metrics()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Users", metrics["total_users"])
        col2.metric("Faculty",     metrics["faculty"])
        col3.metric("Students",    metrics["students"])
        col4.metric("Admins",      metrics["admins"])


def _faculty_dashboard(user, active_sem):
    sem_id = active_sem["id"] if active_sem else None
    assignments = CourseService.get_faculty_courses(user.id, sem_id)

    col1, col2 = st.columns(2)
    col1.metric("My Courses This Semester", len(assignments))
    total_students = sum(
        CourseService.get_enrollment_count(a["courses"]["id"])
        for a in assignments if a.get("courses")
    )
    col2.metric("Total Students", total_students)

    if assignments:
        st.divider()
        section_header("My Courses This Semester")
        for a in assignments:
            course   = a.get("courses", {})
            dept     = (course.get("departments") or {}).get("name", "—")
            enrolled = CourseService.get_enrollment_count(course["id"])
            st.markdown(
                f"📘 **{course.get('code','—')}** — {course.get('name','—')} "
                f"&nbsp;|&nbsp; {dept} "
                f"&nbsp;|&nbsp; {enrolled}/{course.get('max_students','—')} students"
            )


def _student_dashboard(user, active_sem):
    st.info("Enrollment and grades will appear here in Phase 2 & 3.")
