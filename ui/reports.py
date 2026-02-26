"""
Phase 5 — Reports & Analytics UI
Used by admin (all courses), faculty (assigned courses), student (own data).
"""
import streamlit as st
import pandas as pd
from services.reports_service import ReportsService
from services.semester_service import SemesterService
from services.course_service import CourseService
from services.grading_service import GradingService
from ui.styles import (page_header, section_header, stat_card,
                       grade_badge, status_badge, BRAND)


# ── Colour helpers ────────────────────────────────────────────────

GRADE_COLOURS = {
    "A":"#2e9e6e","A-":"#3ab87e",
    "B+":"#307890","B":"#3a8aa0","B-":"#4a9ab0",
    "C+":"#c8900a","C":"#d8a020","C-":"#e0b030",
    "D+":"#c06020","D":"#d07030",
    "F":"#c83030","—":"#aaaaaa",
}


def _sem_selector(key_prefix: str) -> tuple[str | None, str]:
    sems = SemesterService.get_all()
    active = SemesterService.get_active()
    if not sems:
        return None, "—"
    sem_map = {s["name"]: s["id"] for s in sems}
    names = list(sem_map.keys())
    default = active["name"] if active and active["name"] in names else names[0]
    sel = st.selectbox("Semester", ["All Semesters"] + names,
                        index=names.index(default) + 1, key=f"{key_prefix}_sem")
    if sel == "All Semesters":
        return None, "All"
    return sem_map[sel], sel


# ══════════════════════════════════════════════════════════════════
# ADMIN REPORTS
# ══════════════════════════════════════════════════════════════════

def render_admin_reports() -> None:
    page_header("📈", "Reports & Analytics", "Institution-wide insights")

    tab_overview, tab_course, tab_enroll, tab_faculty, tab_completion, tab_semester = st.tabs([
        "🏠 Overview",
        "📊 Course Performance",
        "🎓 Enrollment",
        "👨‍🏫 Faculty Workload",
        "✅ Gradebook Status",
        "📅 Semester Comparison",
    ])

    # ── Overview ───────────────────────────────────────────────────
    with tab_overview:
        section_header("Institution Overview", "Live counts across the platform")
        with st.spinner("Loading..."):
            summary = ReportsService.admin_summary()

        c1,c2,c3 = st.columns(3)
        with c1: stat_card("Total Students",  str(summary.get("total_students",0)))
        with c2: stat_card("Total Faculty",   str(summary.get("total_faculty",0)))
        with c3: stat_card("Active Courses",  str(summary.get("total_courses",0)))
        st.markdown("<br>", unsafe_allow_html=True)
        c4,c5,c6 = st.columns(3)
        with c4: stat_card("Active Enrollments", str(summary.get("total_enrolled",0)))
        with c5: stat_card("Grades Pending Approval",
                            str(summary.get("pending_grades",0)),
                            "Submitted by faculty")
        with c6: stat_card("Grades Released",
                            str(summary.get("released_grades",0)),
                            "Visible to students")

    # ── Course Performance ─────────────────────────────────────────
    with tab_course:
        page_header("📊", "Course Performance", "Grade distributions and pass rates")
        sem_id, sem_name = _sem_selector("adm_course_perf")
        courses = CourseService.get_all(sem_id)
        if not courses:
            st.info("No courses found.")
        else:
            opts = {f"{c['code']} — {c['name']}": c for c in courses}
            sel  = st.selectbox("Select Course", list(opts.keys()), key="adm_cp_course")
            c    = opts[sel]
            _render_course_performance(c["id"], c)

    # ── Enrollment ─────────────────────────────────────────────────
    with tab_enroll:
        page_header("🎓", "Enrollment Analytics", "Students per course and fill rates")
        sem_id, sem_name = _sem_selector("adm_enroll")
        with st.spinner("Loading enrollment data..."):
            data = ReportsService.enrollment_by_semester(sem_id)
        _render_enrollment_table(data)

    # ── Faculty Workload ──────────────────────────────────────────
    with tab_faculty:
        page_header("👨‍🏫", "Faculty Workload", "Courses and students per faculty member")
        sem_id, sem_name = _sem_selector("adm_faculty_wl")
        with st.spinner("Loading..."):
            data = ReportsService.faculty_workload(sem_id)
        _render_faculty_workload(data)

    # ── Gradebook Completion ──────────────────────────────────────
    with tab_completion:
        page_header("✅", "Gradebook Status", "Track submission and release progress")
        sem_id, sem_name = _sem_selector("adm_gb_status")
        with st.spinner("Loading..."):
            data = ReportsService.gradebook_completion(sem_id)
        _render_gradebook_completion(data)

    # ── Semester Comparison ───────────────────────────────────────
    with tab_semester:
        page_header("📅", "Semester Comparison", "Performance trends across semesters")
        with st.spinner("Loading..."):
            data = ReportsService.semester_comparison()
        _render_semester_comparison(data)


# ══════════════════════════════════════════════════════════════════
# FACULTY REPORTS
# ══════════════════════════════════════════════════════════════════

def render_faculty_reports(faculty_user_id: str) -> None:
    page_header("📈", "My Reports", "Analytics for your assigned courses")

    sem_id, sem_name = _sem_selector("fac_rep")
    assignments = CourseService.get_faculty_courses(faculty_user_id, sem_id)
    if not assignments:
        st.info("No courses assigned for this semester.")
        return

    course_opts = {
        f"{a['courses']['code']} — {a['courses']['name']}": a["courses"]
        for a in assignments if a.get("courses")
    }
    sel   = st.selectbox("Course", list(course_opts.keys()), key="fac_rep_course")
    course = course_opts[sel]

    tab_perf, tab_enroll, tab_gb = st.tabs([
        "📊 Grade Distribution",
        "🎓 Enrollment",
        "✅ Gradebook Status",
    ])

    with tab_perf:
        _render_course_performance(course["id"], course)

    with tab_enroll:
        data = ReportsService.enrollment_by_semester(sem_id)
        data = [d for d in data if d["code"] == course.get("code")]
        _render_enrollment_table(data)

    with tab_gb:
        data = ReportsService.gradebook_completion(sem_id)
        data = [d for d in data if d["code"] == course.get("code")]
        _render_gradebook_completion(data)


# ══════════════════════════════════════════════════════════════════
# STUDENT REPORTS (transcript + GPA)
# ══════════════════════════════════════════════════════════════════

def render_student_reports(student_id: str) -> None:
    page_header("📄", "My Transcript & Analytics", "Your academic record")

    with st.spinner("Loading your transcript..."):
        data = ReportsService.student_transcript(student_id)

    if not data or not data.get("grades"):
        st.info("No released grades yet. Grades appear here once released by your faculty.")
        return

    profile     = data["profile"]
    sem_map     = data["semester_map"]
    total_creds = data["total_credits"]
    cgpa        = data["cgpa"]

    # ── Header stats ──────────────────────────────────────────────
    full_name = (profile.get("full_name") or
                 f"{profile.get('first_name','')} {profile.get('last_name','')}").strip()
    section_header(f"Academic Record — {full_name}")
    c1,c2,c3,c4 = st.columns(4)
    with c1: stat_card("CGPA",           f"{cgpa:.2f}" if cgpa else "—")
    with c2: stat_card("Total Credits",  str(int(total_creds)))
    with c3: stat_card("Semesters",      str(len(sem_map)))
    with c4: stat_card("Courses Graded", str(len(data["grades"])))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── GPA trend chart ───────────────────────────────────────────
    section_header("GPA by Semester")
    sem_gpas = []
    for sem_name, courses in sem_map.items():
        creds = sum(c["credits"] for c in courses)
        qual  = sum(c["gpa_points"] * c["credits"] for c in courses)
        sem_gpa = round(qual / creds, 2) if creds else None
        if sem_gpa:
            sem_gpas.append({"Semester": sem_name, "GPA": sem_gpa})
    if sem_gpas:
        chart_df = pd.DataFrame(sem_gpas).set_index("Semester")
        st.line_chart(chart_df, use_container_width=True, height=220,
                      color=BRAND["core"])

    st.divider()

    # ── Semester-by-semester breakdown ────────────────────────────
    section_header("Course-by-Course Transcript")
    for sem_name, courses in sem_map.items():
        sem_creds = sum(c["credits"] for c in courses)
        sem_qual  = sum(c["gpa_points"] * c["credits"] for c in courses)
        sem_gpa   = round(sem_qual / sem_creds, 2) if sem_creds else None
        with st.expander(
            f"📅 {sem_name}  |  GPA: {sem_gpa or '—'}  |  "
            f"{len(courses)} course(s)  |  {int(sem_creds)} credits"
        ):
            rows = []
            for c in courses:
                rows.append({
                    "Course":       f"{c['code']} — {c['name']}",
                    "Credits":      int(c["credits"]),
                    "Total Score":  f"{c['total_score']:.1f}" if c.get('total_score') else "—",
                    "Grade":        c["letter_grade"] or "—",
                    "GPA Points":   c["gpa_points"],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # ── Grade distribution pie-style bar ─────────────────────────
    section_header("Your Grade Distribution")
    from collections import Counter
    all_grades = [c["letter_grade"] for sem in sem_map.values()
                  for c in sem if c.get("letter_grade")]
    counts = Counter(all_grades)
    if counts:
        dist_df = pd.DataFrame(
            [{"Grade": k, "Count": v} for k, v in sorted(counts.items())]
        ).set_index("Grade")
        st.bar_chart(dist_df, use_container_width=True, height=180)


# ══════════════════════════════════════════════════════════════════
# Shared renderers
# ══════════════════════════════════════════════════════════════════

def _render_course_performance(course_uuid: str, course: dict) -> None:
    section_header(
        f"{course.get('code','—')} — {course.get('name','—')}",
        f"Course ID: {course.get('course_id','—')}"
    )
    with st.spinner("Computing grade distribution..."):
        perf = ReportsService.course_grade_distribution(course_uuid)
    if not perf or not perf.get("total"):
        st.info("No compiled grades yet for this course.")
        return

    c1,c2,c3,c4 = st.columns(4)
    with c1: stat_card("Students Graded", str(perf["total"]))
    with c2: stat_card("Pass Rate",       f"{perf['pass_rate']}%",
                        f"{perf['passed']} passed")
    with c3: stat_card("Average Score",   str(perf["avg_score"]))
    with c4: stat_card("Highest / Lowest",
                        f"{perf['highest']} / {perf['lowest']}")

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Grade Distribution")
    dist = perf.get("distribution", {})
    if dist:
        order = ["A","A-","B+","B","B-","C+","C","C-","D+","D","F","—"]
        ordered = {g: dist.get(g,0) for g in order if g in dist}
        df = pd.DataFrame(
            [{"Grade": k, "Students": v} for k,v in ordered.items()]
        ).set_index("Grade")
        st.bar_chart(df, use_container_width=True, height=220,
                     color=BRAND["core"])

        # Table
        rows = [{"Grade": k, "Count": v,
                 "Percentage": f"{round(v/perf['total']*100,1)}%"}
                for k,v in ordered.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True,
                     hide_index=True)

    # Pass vs Fail
    st.divider()
    section_header("Pass vs Fail")
    pf_df = pd.DataFrame(
        [{"Result": "Pass", "Count": perf["passed"]},
         {"Result": "Fail", "Count": perf["failed"]}]
    ).set_index("Result")
    st.bar_chart(pf_df, use_container_width=True, height=160)


def _render_enrollment_table(data: list) -> None:
    if not data:
        st.info("No enrollment data found.")
        return
    rows = [{
        "Course ID":   d["course_id"],
        "Code":        d["code"],
        "Course Name": d["name"],
        "Semester":    d["semester"],
        "Enrolled":    d["enrolled"],
        "Capacity":    d["max_students"],
        "Fill Rate":   f"{d['fill_rate']}%",
    } for d in data]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Enrollment vs Capacity")
    chart_df = pd.DataFrame([{
        "Course": d["code"], "Enrolled": d["enrolled"],
        "Capacity": d["max_students"]
    } for d in data]).set_index("Course")
    st.bar_chart(chart_df, use_container_width=True, height=240)


def _render_faculty_workload(data: list) -> None:
    if not data:
        st.info("No faculty workload data found.")
        return
    rows = [{
        "Faculty":         d["name"],
        "Courses Assigned": d["num_courses"],
        "Total Students":  d["total_students"],
        "Course List":     ", ".join(d["courses"]),
    } for d in data]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Courses per Faculty")
    chart_df = pd.DataFrame([{
        "Faculty": d["name"].split(" ")[0],
        "Courses": d["num_courses"],
    } for d in data]).set_index("Faculty")
    st.bar_chart(chart_df, use_container_width=True, height=220,
                 color=BRAND["accent"])


def _render_gradebook_completion(data: list) -> None:
    if not data:
        st.info("No gradebook status data found.")
        return

    status_icons = {
        "released":    "📢 Released",
        "approved":    "✅ Approved",
        "submitted":   "📤 Submitted",
        "draft":       "✏️ Draft",
        "not_started": "⭕ Not Started",
    }

    rows = [{
        "Code":       d["code"],
        "Course":     d["name"],
        "Semester":   d["semester"],
        "Enrolled":   d["enrolled"],
        "Graded":     d["graded"],
        "Status":     status_icons.get(d["status"], d["status"]),
    } for d in data]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Status Summary")
    from collections import Counter
    counts = Counter(d["status"] for d in data)
    count_df = pd.DataFrame(
        [{"Status": status_icons.get(k,k), "Courses": v}
         for k,v in counts.items()]
    ).set_index("Status")
    st.bar_chart(count_df, use_container_width=True, height=180)


def _render_semester_comparison(data: list) -> None:
    if not data:
        st.info("No semester data found.")
        return
    rows = [{
        "Semester":   d["semester"],
        "Courses":    d["courses"],
        "Students":   d["students"],
        "Avg Score":  d["avg_score"] or "—",
        "Pass Rate":  f"{d['pass_rate']}%" if d["pass_rate"] else "—",
    } for d in data]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    chart_data = [d for d in data if d.get("avg_score")]
    if chart_data:
        section_header("Average Score by Semester")
        cdf = pd.DataFrame([{
            "Semester": d["semester"], "Avg Score": d["avg_score"]
        } for d in chart_data]).set_index("Semester")
        st.line_chart(cdf, use_container_width=True, height=200,
                      color=BRAND["core"])

    pass_data = [d for d in data if d.get("pass_rate")]
    if pass_data:
        section_header("Pass Rate by Semester")
        pdf = pd.DataFrame([{
            "Semester": d["semester"], "Pass Rate %": d["pass_rate"]
        } for d in pass_data]).set_index("Semester")
        st.bar_chart(pdf, use_container_width=True, height=200,
                     color=BRAND["accent"])
