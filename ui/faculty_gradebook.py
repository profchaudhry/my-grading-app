"""
Faculty Gradebook page — plugged into faculty_console.
Tab order: Quizzes → Assignments → Midterm → Final → Summary → Scheme
"""
import streamlit as st
from services.course_service import CourseService
from services.enrollment_service import EnrollmentService
from services.semester_service import SemesterService
from ui.gradebook import (
    render_scheme_editor, render_quiz_manager,
    render_assignment_manager, render_exam_manager,
    render_gradebook_summary,
)
from ui.styles import section_header


def render_faculty_gradebook(faculty_user_id: str) -> None:
    st.title("📒 Gradebook")

    sems       = SemesterService.get_all()
    active_sem = SemesterService.get_active()

    if not sems:
        st.warning("No semesters found.")
        return

    sem_map   = {s["name"]: s["id"] for s in sems}
    sem_names = list(sem_map.keys())
    default   = active_sem["name"] if active_sem and active_sem["name"] in sem_names \
                else sem_names[0]

    sel_sem_name = st.selectbox("Semester", sem_names,
                                 index=sem_names.index(default), key="gb_sem")
    sel_sem_id   = sem_map[sel_sem_name]

    assignments = CourseService.get_faculty_courses(faculty_user_id, sel_sem_id)
    if not assignments:
        st.info("No courses assigned to you for this semester.")
        return

    course_map = {
        f"{a['courses']['code']} — {a['courses']['name']} [{a['courses'].get('course_id','—')}]":
        a["courses"]
        for a in assignments if a.get("courses")
    }
    sel_label   = st.selectbox("Course", list(course_map.keys()), key="gb_course")
    course      = course_map[sel_label]
    course_uuid = course["id"]

    enrollments = EnrollmentService.get_course_enrollments(course_uuid)
    if not enrollments:
        st.warning("No students enrolled in this course.")
        return

    st.caption(f"👥 {len(enrollments)} enrolled student(s)")
    st.divider()

    # Tab order: Quizzes → Assignments → Midterm → Final → Summary → Scheme
    t_quiz, t_asgn, t_mid, t_fin, t_summary, t_scheme = st.tabs([
        "📝 Quizzes", "📄 Assignments",
        "📘 Midterm", "📗 Final",
        "📊 Summary & Submit", "⚙️ Scheme",
    ])

    with t_quiz:
        render_quiz_manager(course_uuid, enrollments)
    with t_asgn:
        render_assignment_manager(course_uuid, enrollments)
    with t_mid:
        render_exam_manager(course_uuid, enrollments, exam_type="midterm")
    with t_fin:
        render_exam_manager(course_uuid, enrollments, exam_type="final")
    with t_summary:
        render_gradebook_summary(course_uuid, enrollments,
                                  can_submit=True, can_approve=False)
    with t_scheme:
        render_scheme_editor(course_uuid, is_admin=False)
