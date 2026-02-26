"""
Faculty Ultra Console — all Faculty features + UPro Grade.
"""
import streamlit as st
from core.layout import base_console
from core.guards import require_role, require_approval
from services.profile_service import ProfileService
from services.course_service import CourseService
from services.semester_service import SemesterService
from services.enrollment_service import EnrollmentService
from ui.dashboard import render_dashboard
from ui.components import render_change_password
from ui.bulk_enrollment import render_bulk_enrollment
from ui.faculty_gradebook import render_faculty_gradebook
from ui.reports import render_faculty_reports
from ui.upro_grade import render_upro_grade
from ui.styles import section_header


@require_role(["faculty_ultra"])
def faculty_ultra_console() -> None:

    user    = st.session_state.user
    profile = ProfileService.get_profile(user.id)

    require_approval(profile)

    if not profile:
        st.error("Profile could not be loaded.")
        return

    st.session_state.profile = profile

    menu = base_console(
        "Faculty Ultra Panel",
        [
            "📊 Dashboard",
            "📚 My Courses",
            "📋 Bulk Enrollment",
            "📒 Gradebook",
            "📈 Reports",
            "🏆 UPro Grade",
            "👤 My Profile",
            "🔒 Change Password",
        ]
    )

    if menu == "📊 Dashboard":
        render_dashboard()

    elif menu == "📚 My Courses":
        st.title("📚 My Courses")
        sems       = SemesterService.get_all()
        active_sem = SemesterService.get_active()
        if not sems:
            st.warning("No semesters.")
            return
        sem_map   = {s["name"]: s["id"] for s in sems}
        sem_names = list(sem_map.keys())
        default   = active_sem["name"] if active_sem and active_sem["name"] in sem_names \
                    else sem_names[0]
        sel_sem   = st.selectbox("Semester", sem_names, index=sem_names.index(default))
        sel_sem_id = sem_map[sel_sem]
        assignments = CourseService.get_faculty_courses(user.id, sel_sem_id)
        if not assignments:
            st.info("No courses assigned for this semester.")
            return
        section_header("Assigned Courses", f"{len(assignments)}")
        for a in assignments:
            course  = a.get("courses", {}) or {}
            dept    = (course.get("departments") or {}).get("name","—")
            cid     = course.get("course_id","—")
            enrolled = CourseService.get_enrollment_count(course["id"])
            with st.expander(
                f"📘 **{course.get('code','—')}** — {course.get('name','—')} "
                f"| ID: `{cid}` | {dept} | {enrolled} enrolled"
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Course ID",    cid)
                c2.metric("Credits",      course.get("credits","—"))
                c3.metric("Max Students", course.get("max_students","—"))
                c4.metric("Enrolled",     enrolled)

    elif menu == "📋 Bulk Enrollment":
        all_assignments = CourseService.get_faculty_courses(user.id)
        allowed_cids    = {
            a["courses"]["course_id"]
            for a in all_assignments
            if a.get("courses") and a["courses"].get("course_id")
        }
        render_bulk_enrollment(domain_default="um.ar",
                                allowed_course_ids=allowed_cids,
                                role="faculty_ultra")

    elif menu == "📒 Gradebook":
        render_faculty_gradebook(user.id)

    elif menu == "📈 Reports":
        render_faculty_reports(user.id)

    elif menu == "🏆 UPro Grade":
        st.title("🏆 UPro Grade")
        sems       = SemesterService.get_all()
        active_sem = SemesterService.get_active()
        if not sems:
            st.warning("No semesters found.")
            return
        sem_map   = {s["name"]: s["id"] for s in sems}
        sem_names = list(sem_map.keys())
        default   = active_sem["name"] if active_sem and active_sem["name"] in sem_names \
                    else sem_names[0]
        sel_sem   = st.selectbox("Semester", sem_names,
                                  index=sem_names.index(default), key="upro_sem")
        sel_sem_id = sem_map[sel_sem]
        assignments = CourseService.get_faculty_courses(user.id, sel_sem_id)
        if not assignments:
            st.info("No courses assigned for this semester.")
            return
        course_options = {
            f"{a['courses']['code']} — {a['courses']['name']} [{a['courses'].get('course_id','—')}]": a["courses"]
            for a in assignments if a.get("courses")
        }
        sel_label   = st.selectbox("Course", list(course_options.keys()), key="upro_course")
        course      = course_options[sel_label]
        course_uuid = course["id"]
        course_info = {
            "code":      course.get("code",""),
            "name":      course.get("name",""),
            "course_id": course.get("course_id",""),
            "semester":  sel_sem,
        }
        st.divider()
        render_upro_grade(course_uuid, course_info, is_admin=False)

    elif menu == "👤 My Profile":
        st.title("👤 My Profile")
        fresh = ProfileService.get_profile(user.id)
        if fresh:
            profile = fresh
            st.session_state.profile = fresh
        section_header("Identity", "Contact admin to update these fields")
        c1, c2 = st.columns(2)
        c1.markdown(f"**First Name:** {profile.get('first_name','—') or '—'}")
        c2.markdown(f"**Last Name:** {profile.get('last_name','—') or '—'}")
        c1.markdown(f"**Employee ID:** {profile.get('employee_id','—') or '—'}")
        c2.markdown(f"**Email:** {user.email}")
        st.divider()
        section_header("Profile Details")
        with st.form("fu_profile_form"):
            c1, c2  = st.columns(2)
            phone   = c1.text_input("Phone", value=profile.get("phone","") or "")
            office  = c2.text_input("Office", value=profile.get("office_location","") or "")
            qual    = c1.text_input("Qualification", value=profile.get("qualification","") or "")
            spec    = c2.text_input("Specialization", value=profile.get("specialization","") or "")
            address = st.text_input("Address", value=profile.get("address","") or "")
            submitted = st.form_submit_button("💾 Save", use_container_width=True)
        if submitted:
            updates = {"phone": phone, "office_location": office,
                       "qualification": qual, "specialization": spec, "address": address}
            with st.spinner("Saving..."):
                ok = ProfileService.update_profile(user.id, updates)
            if ok:
                st.session_state.profile.update(updates)
                st.success("✅ Profile updated.")
            else:
                st.error("❌ Save failed.")

    elif menu == "🔒 Change Password":
        st.title("🔒 Change Password")
        st.divider()
        render_change_password()
