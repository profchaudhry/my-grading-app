import streamlit as st
from core.layout import base_console
from core.guards import require_role
from services.profile_service import ProfileService
from services.enrollment_service import EnrollmentService
from ui.dashboard import render_dashboard
from ui.components import render_change_password
from services.supabase_client import supabase
from services.grading_service import GradingService, score_to_letter
from ui.reports import render_student_reports
from ui.communications import render_student_announcements
from services.upro_service import UProService
from ui.styles import section_header


@require_role(["student"])
def student_console() -> None:

    user    = st.session_state.user
    profile = st.session_state.get("profile") or {}

    menu = base_console(
        "Student Panel",
        [
            "📊 Dashboard",
            "📚 My Courses",
            "📋 Announcements",
            "📊 My Grades",
            "📄 My Transcript",
            "🏆 UPro Grades",
            "🏷️ My Syndicate",
            "👤 My Profile",
            "🔒 Change Password",
        ]
    )

    # ==============================================================
    # DASHBOARD
    # ==============================================================
    if menu == "📊 Dashboard":
        render_dashboard()

    # ==============================================================
    # MY COURSES
    # ==============================================================
    elif menu == "📚 My Courses":
        st.title("📚 My Enrolled Courses")

        enrollments = EnrollmentService.get_student_enrollments(user.id)
        if not enrollments:
            st.info("You are not enrolled in any courses yet.")
        else:
            section_header("Enrolled Courses", f"{len(enrollments)} course(s)")
            for e in enrollments:
                course = e.get("courses", {}) or {}
                dept   = (course.get("departments") or {}).get("name", "—")
                sem    = (e.get("semesters") or {}).get("name", "—")
                cid    = course.get("course_id", "—")
                with st.expander(
                    f"📘 **{course.get('code','—')}** — {course.get('name','—')} "
                    f"| ID: `{cid}` | {sem}"
                ):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Course ID:** `{cid}`")
                    c2.markdown(f"**Department:** {dept}")
                    c3.markdown(f"**Credits:** {course.get('credits','—')}")
                    if course.get("description"):
                        st.markdown(f"**Description:** {course['description']}")


    # ==============================================================
    # MY GRADES
    # ==============================================================
    elif menu == "📊 My Grades":
        st.title("📊 My Grades")

        grades = GradingService.get_student_grades(user.id)

        if not grades:
            st.info("No grades have been released yet. Check back after your faculty submits and admin approves your grades.")
        else:
            from ui.styles import section_header

            # GPA summary
            gpa_vals = [g["gpa_points"] for g in grades if g.get("gpa_points") is not None]
            cgpa = round(sum(gpa_vals) / len(gpa_vals), 2) if gpa_vals else None

            c1, c2 = st.columns(2)
            c1.metric("Courses with Released Grades", len(grades))
            if cgpa is not None:
                c2.metric("CGPA", cgpa)

            st.divider()
            section_header("Course Grades")

            grade_colours = {
                "A": "🟢", "A-": "🟢",
                "B+": "🔵", "B": "🔵", "B-": "🔵",
                "C+": "🟡", "C": "🟡", "C-": "🟡",
                "D+": "🟠", "D": "🟠",
                "F": "🔴",
            }

            for g in grades:
                course  = g.get("courses", {}) or {}
                letter  = g.get("letter_grade") or "—"
                total   = g.get("total_score")
                icon    = grade_colours.get(letter, "⚪")

                with st.expander(
                    f"{icon} **{course.get('code','—')}** — {course.get('name','—')} "
                    f"| Grade: **{letter}** | Total: {f'{total:.2f}' if total else '—'}"
                ):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Quiz",       f"{g.get('quiz_score','—')}")
                    c2.metric("Assignment", f"{g.get('assignment_score','—')}")
                    c3.metric("Midterm",    f"{g.get('midterm_score','—')}")
                    c4.metric("Final",      f"{g.get('final_score','—')}")
                    c5.metric("Total",      f"{total:.2f}" if total else "—")
                    st.markdown(
                        f"**Letter Grade:** {icon} **{letter}** &nbsp;&nbsp;"
                        f"**GPA Points:** {g.get('gpa_points','—')} &nbsp;&nbsp;"
                        f"**Credits:** {course.get('credits','—')}"
                    )


    # ==============================================================
    # UPRO GRADES (released AOL grades)
    # ==============================================================
    elif menu == "📋 Announcements":
        enrolled = [e["course_id"] for e in (supabase.table("enrollments").select("course_id").eq("student_id", user.id).eq("status","active").execute().data or [])]
        render_student_announcements(user.id, role, enrolled)

    elif menu == "📄 My Transcript":
        render_student_reports(user.id)

    elif menu == "🏆 UPro Grades":
        st.title("🏆 UPro Grades")
        aol_grades = UProService.get_student_aol_grades(user.id)
        if not aol_grades:
            st.info("No UPro grades have been released yet.")
        else:
            from ui.styles import section_header
            section_header("Released UPro (AOL) Grades")
            for g in aol_grades:
                course = g.get("courses", {}) or {}
                letter = g.get("letter_grade") or "—"
                total  = g.get("grand_total")
                icons  = {"A":"🟢","A-":"🟢","B+":"🔵","B":"🔵","B-":"🔵",
                           "C+":"🟡","C":"🟡","C-":"🟡","D+":"🟠","D":"🟠","F":"🔴"}
                icon   = icons.get(letter,"⚪")
                with st.expander(
                    f"{icon} **{course.get('code','—')}** — {course.get('name','—')} "
                    f"| Grade: **{letter}** | Total: {f'{total:.2f}' if total else '—'}"
                ):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Quiz",       f"{g.get('quiz_total','—')}")
                    c2.metric("Assignment", f"{g.get('assignment_total','—')}")
                    c3.metric("Midterm",    f"{g.get('midterm_total','—')}")
                    c4.metric("Final",      f"{g.get('final_total','—')}")
                    c5.metric("Total",      f"{total:.2f}" if total else "—")
                    st.markdown(f"**Letter Grade:** {icon} **{letter}** | **GPA:** {g.get('gpa_points','—')}")

    # ==============================================================
    # MY SYNDICATE
    # ==============================================================
    elif menu == "🏷️ My Syndicate":
        st.title("🏷️ My Syndicate")

        from services.enrollment_service import EnrollmentService
        from ui.styles import section_header

        enrollments = EnrollmentService.get_student_enrollments(user.id)
        if not enrollments:
            st.info("You are not enrolled in any courses.")
        else:
            course_map = {
                f"{e['courses']['code']} — {e['courses']['name']}": e["courses"]
                for e in enrollments if e.get("courses")
            }
            sel_label   = st.selectbox("Select Course", list(course_map.keys()))
            course      = course_map[sel_label]
            course_uuid = course["id"]

            # Check existing syndicate
            membership = UProService.get_student_syndicate(course_uuid, user.id)
            if membership:
                syn = membership.get("syndicates", {}) or {}
                status = syn.get("status","—")
                status_icons = {"confirmed":"✅","pending":"⏳","rejected":"❌"}
                st.info(
                    f"You are in syndicate: **{syn.get('name','—')}** | "
                    f"Status: {status_icons.get(status,'')} {status.capitalize()}"
                )
                members = UProService.get_syndicate_members(membership["syndicate_id"])
                if members:
                    section_header("Syndicate Members")
                    for m in members:
                        mp = m.get("profiles",{}) or {}
                        is_lead = mp.get("id") == syn.get("lead_student_id")
                        st.caption(f"{'👑 Lead: ' if is_lead else '👤 '}{(mp.get('full_name') or mp.get('first_name',''))} `{mp.get('enrollment_number','')}`")
            else:
                st.warning("You are not in a syndicate for this course yet.")
                st.divider()
                section_header("Submit Syndicate Details",
                                "Submit your syndicate name and lead for faculty confirmation")
                with st.form("submit_syndicate_form"):
                    syn_name  = st.text_input("Syndicate Name", placeholder="e.g. Alpha Team")
                    lead_name = st.text_input(
                        "Syndicate Lead Name",
                        placeholder="Enter the full name of the syndicate lead",
                        help="Must be an enrolled student in this course"
                    )
                    st.caption("Your submission will be reviewed and confirmed by faculty.")
                    submitted = st.form_submit_button("Submit Syndicate", use_container_width=True)

                if submitted:
                    if not syn_name or not lead_name:
                        st.error("Both syndicate name and lead name are required.")
                    else:
                        # Try to find lead in enrolled students
                        enrolled = EnrollmentService.get_course_enrollments(course_uuid)
                        lead_profile = None
                        for e in enrolled:
                            p = e.get("profiles",{}) or {}
                            pname = (p.get("full_name") or f"{p.get('first_name','')} {p.get('last_name','')}").strip().lower()
                            if pname == lead_name.strip().lower():
                                lead_profile = p
                                break

                        result = UProService.create_syndicate(
                            course_uuid, syn_name,
                            lead_student_id=lead_profile["id"] if lead_profile else None,
                            created_by_role="student",
                            status="pending",
                        )
                        if result:
                            # Add submitting student as first member
                            UProService.add_member(result["id"], course_uuid, user.id)
                            st.success(
                                "✅ Syndicate submitted! It will appear here once faculty confirms it."
                            )
                            st.rerun()
                        else:
                            st.error("❌ Submission failed. A syndicate with this name may already exist.")


    # ==============================================================
    # MY PROFILE
    # ==============================================================
    elif menu == "👤 My Profile":
        st.title("👤 My Profile")

        fresh = ProfileService.get_profile(user.id)
        if fresh:
            profile = fresh
            st.session_state.profile = fresh

        # ── Read-only fields ──
        section_header(
            "Personal Information",
            "Contact your administrator to update these fields"
        )
        c1, c2 = st.columns(2)
        # full_name is shown as one field; fall back to first+last if full_name not set
        display_name = profile.get("full_name","").strip() or \
                       f"{profile.get('first_name','') or ''} {profile.get('last_name','') or ''}".strip()
        c1.markdown(f"**Full Name:** {display_name or '—'}")
        c2.markdown(f"**Enrollment Number:** {profile.get('enrollment_number','—') or '—'}")
        c1.markdown(f"**Program:** {profile.get('program','—') or '—'}")
        c2.markdown(f"**Year of Study:** {profile.get('year_of_study','—') or '—'}")
        c1.markdown(f"**Date of Birth:** {profile.get('date_of_birth','—') or '—'}")
        c2.markdown(f"**Email:** {user.email}")

        st.divider()

        # ── Editable fields ──
        section_header("Contact Information", "You can update this field")

        with st.form("student_profile_form"):
            phone = st.text_input(
                "Phone Number",
                value=profile.get("phone", "") or "",
                placeholder="e.g. +92 300 1234567"
            )
            submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

        if submitted:
            with st.spinner("Saving..."):
                ok = ProfileService.update_profile(user.id, {"phone": phone.strip()})
            if ok:
                st.session_state.profile["phone"] = phone.strip()
                st.success("✅ Profile updated successfully.")
            else:
                st.error("❌ Save failed. Please try again.")

    # ==============================================================
    # CHANGE PASSWORD
    # ==============================================================
    elif menu == "🔒 Change Password":
        st.title("🔒 Change Password")
        st.divider()
        render_change_password()
