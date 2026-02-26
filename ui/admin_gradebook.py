"""
Admin Gradebook page — plugged into admin_console.
Admin can manage any course, edit global scheme, approve and release grades.
"""
import streamlit as st
from services.course_service import CourseService
from services.enrollment_service import EnrollmentService
from services.semester_service import SemesterService
from services.grading_service import GradingService
from ui.gradebook import (
    render_scheme_editor, render_quiz_manager,
    render_assignment_manager, render_exam_manager,
    render_gradebook_summary,
)
from ui.styles import section_header


def render_admin_gradebook() -> None:
    st.title("📒 Gradebook — Admin")

    tab_global, tab_course, tab_pending = st.tabs([
        "🌐 Global Scheme",
        "📚 Course Gradebook",
        "✅ Pending Approval",
    ])

    # ── Global scheme editor ──────────────────────────────────────
    with tab_global:
        section_header("Global Grading Scheme",
                        "Default scheme used by all courses unless overridden")
        # Render using the global scheme directly
        scheme = GradingService.get_global_scheme()
        with st.form("global_scheme_form"):
            section_header("Component Weights", "Must sum to 100")
            c1, c2, c3, c4 = st.columns(4)
            w_quiz = c1.number_input("Quiz %",       min_value=0.0, max_value=100.0,
                                      value=float(scheme["weight_quiz"]),      step=1.0)
            w_asgn = c2.number_input("Assignment %", min_value=0.0, max_value=100.0,
                                      value=float(scheme["weight_assignment"]), step=1.0)
            w_mid  = c3.number_input("Midterm %",    min_value=0.0, max_value=100.0,
                                      value=float(scheme["weight_midterm"]),    step=1.0)
            w_fin  = c4.number_input("Final %",      min_value=0.0, max_value=100.0,
                                      value=float(scheme["weight_final"]),      step=1.0)
            st.divider()
            section_header("Letter Grade Thresholds")
            r1c1,r1c2,r1c3,r1c4,r1c5 = st.columns(5)
            g_a  = r1c1.number_input("A ≥",  value=float(scheme["grade_a_min"]),   step=1.0)
            g_am = r1c2.number_input("A- ≥", value=float(scheme["grade_a_m_min"]), step=1.0)
            g_bp = r1c3.number_input("B+ ≥", value=float(scheme["grade_bp_min"]),  step=1.0)
            g_b  = r1c4.number_input("B ≥",  value=float(scheme["grade_b_min"]),   step=1.0)
            g_bm = r1c5.number_input("B- ≥", value=float(scheme["grade_b_m_min"]), step=1.0)
            r2c1,r2c2,r2c3,r2c4,r2c5 = st.columns(5)
            g_cp = r2c1.number_input("C+ ≥", value=float(scheme["grade_cp_min"]),  step=1.0)
            g_c  = r2c2.number_input("C ≥",  value=float(scheme["grade_c_min"]),   step=1.0)
            g_cm = r2c3.number_input("C- ≥", value=float(scheme["grade_c_m_min"]), step=1.0)
            g_dp = r2c4.number_input("D+ ≥", value=float(scheme["grade_dp_min"]),  step=1.0)
            g_d  = r2c5.number_input("D ≥",  value=float(scheme["grade_d_min"]),   step=1.0)
            st.caption("F = anything below D threshold")
            submitted = st.form_submit_button("💾 Save Global Scheme",
                                               use_container_width=True)

        if submitted:
            total_w = w_quiz + w_asgn + w_mid + w_fin
            if round(total_w) != 100:
                st.error(f"Weights must sum to 100. Current sum: {total_w}")
            else:
                ok = GradingService.update_global_scheme({
                    "weight_quiz": w_quiz, "weight_assignment": w_asgn,
                    "weight_midterm": w_mid, "weight_final": w_fin,
                    "grade_a_min": g_a, "grade_a_m_min": g_am,
                    "grade_bp_min": g_bp, "grade_b_min": g_b, "grade_b_m_min": g_bm,
                    "grade_cp_min": g_cp, "grade_c_min": g_c, "grade_c_m_min": g_cm,
                    "grade_dp_min": g_dp, "grade_d_min": g_d,
                })
                if ok:
                    st.success("✅ Global scheme updated.")
                    st.rerun()
                else:
                    st.error("❌ Update failed.")

    # ── Course gradebook ──────────────────────────────────────────
    with tab_course:
        sems = SemesterService.get_all()
        if not sems:
            st.warning("No semesters found.")
            return

        sem_map    = {s["name"]: s["id"] for s in sems}
        active_sem = SemesterService.get_active()
        sem_names  = list(sem_map.keys())
        default    = active_sem["name"] if active_sem and active_sem["name"] in sem_names \
                     else sem_names[0]

        sel_sem_name = st.selectbox("Semester", sem_names,
                                     index=sem_names.index(default), key="adm_gb_sem")
        sel_sem_id   = sem_map[sel_sem_name]

        courses = CourseService.get_all(sel_sem_id)
        if not courses:
            st.info("No courses for this semester.")
            return

        course_options = {
            f"{c['code']} — {c['name']} [{c.get('course_id','—')}]": c
            for c in courses
        }
        sel_label   = st.selectbox("Course", list(course_options.keys()), key="adm_gb_course")
        course      = course_options[sel_label]
        course_uuid = course["id"]

        enrollments = EnrollmentService.get_course_enrollments(course_uuid)
        if not enrollments:
            st.warning("No students enrolled in this course.")
        else:
            st.caption(f"👥 {len(enrollments)} enrolled student(s)")
            st.divider()

            tab_scheme, tab_quiz, tab_asgn, tab_mid, tab_fin, tab_summary = st.tabs([
                "⚙️ Scheme", "📝 Quizzes", "📄 Assignments",
                "📘 Midterm", "📗 Final", "📊 Summary & Approve",
            ])

            with tab_scheme:
                render_scheme_editor(course_uuid, is_admin=True)
            with tab_quiz:
                render_quiz_manager(course_uuid, enrollments)
            with tab_asgn:
                render_assignment_manager(course_uuid, enrollments)
            with tab_mid:
                render_exam_manager(course_uuid, enrollments, exam_type="midterm")
            with tab_fin:
                render_exam_manager(course_uuid, enrollments, exam_type="final")
            with tab_summary:
                render_gradebook_summary(
                    course_uuid, enrollments,
                    can_submit=True,
                    can_approve=True,
                )

    # ── Pending approval ──────────────────────────────────────────
    with tab_pending:
        section_header("Grades Pending Approval",
                        "Courses where faculty have submitted grades")
        from services.supabase_client import supabase
        try:
            r = supabase.table("compiled_grades")\
                .select("course_id, status, courses(name, code, course_id)")\
                .eq("status", "submitted")\
                .execute()
            rows = r.data or []
        except Exception:
            rows = []

        if not rows:
            st.success("No grades pending approval.")
        else:
            # Group by course
            seen = {}
            for row in rows:
                cid = row["course_id"]
                if cid not in seen:
                    seen[cid] = row
            for cid, row in seen.items():
                c = row.get("courses", {}) or {}
                with st.container():
                    col1, col2, col3 = st.columns([4, 1, 1])
                    col1.write(
                        f"📘 **{c.get('code','—')}** — {c.get('name','—')} "
                        f"[`{c.get('course_id','—')}`]"
                    )
                    if col2.button("✅ Approve", key=f"appr_{cid}",
                                    use_container_width=True):
                        GradingService.approve_grades(cid)
                        st.success("Approved.")
                        st.rerun()
                    if col3.button("📢 Approve & Release", key=f"rel_{cid}",
                                    use_container_width=True):
                        GradingService.approve_grades(cid)
                        GradingService.release_grades(cid)
                        st.success("Approved and released.")
                        st.rerun()
                st.divider()
