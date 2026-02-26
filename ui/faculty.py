import streamlit as st
from core.layout import base_console
from core.guards import require_role, require_approval
from services.profile_service import ProfileService
from services.course_service import CourseService
from services.semester_service import SemesterService
from ui.dashboard import render_dashboard
from ui.components import render_change_password
from ui.bulk_enrollment import render_bulk_enrollment
from ui.styles import section_header


@require_role(["faculty"])
def faculty_console() -> None:

    user    = st.session_state.user
    profile = ProfileService.get_profile(user.id)

    require_approval(profile)

    if not profile:
        st.error("Your profile could not be loaded. Please contact support.")
        return

    st.session_state.profile = profile

    menu = base_console(
        "Faculty Panel",
        [
            "📊 Dashboard",
            "📚 My Courses",
            "📋 Bulk Enrollment",
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
        st.title("📚 My Courses")

        sems       = SemesterService.get_all()
        active_sem = SemesterService.get_active()

        if sems:
            sem_map      = {s["name"]: s["id"] for s in sems}
            sem_names    = list(sem_map.keys())
            default      = active_sem["name"] if active_sem \
                           and active_sem["name"] in sem_names else sem_names[0]
            sel_sem_name = st.selectbox("Semester", sem_names,
                                         index=sem_names.index(default),
                                         key="faculty_sem_filter")
            sel_sem_id   = sem_map[sel_sem_name]
        else:
            sel_sem_id = None

        with st.spinner("Loading courses..."):
            assignments = CourseService.get_faculty_courses(user.id, sel_sem_id)

        if not assignments:
            st.info("No courses assigned to you for this semester.")
        else:
            section_header("Assigned Courses", f"{len(assignments)} course(s)")
            for a in assignments:
                course   = a.get("courses", {}) or {}
                dept     = (course.get("departments") or {}).get("name", "—")
                enrolled = CourseService.get_enrollment_count(course["id"])
                cid      = course.get("course_id", "—")
                with st.expander(
                    f"📘 **{course.get('code','—')}** — {course.get('name','—')} "
                    f"| ID: `{cid}` | {dept} | {enrolled} enrolled"
                ):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Course ID",    cid)
                    c2.metric("Credits",      course.get("credits", "—"))
                    c3.metric("Max Students", course.get("max_students", "—"))
                    c4.metric("Enrolled",     enrolled)
                    if course.get("description"):
                        st.markdown(f"**Description:** {course['description']}")

    # ==============================================================
    # BULK ENROLLMENT
    # ==============================================================
    elif menu == "📋 Bulk Enrollment":
        # Build the set of course_ids this faculty is allowed to upload to
        all_assignments  = CourseService.get_faculty_courses(user.id)
        allowed_cids     = {
            a["courses"]["course_id"]
            for a in all_assignments
            if a.get("courses") and a["courses"].get("course_id")
        }
        render_bulk_enrollment(
            domain_default="um.ar",
            allowed_course_ids=allowed_cids,
            role="faculty",
        )

    # ==============================================================
    # MY PROFILE
    # ==============================================================
    elif menu == "👤 My Profile":
        st.title("👤 My Profile")

        fresh = ProfileService.get_profile(user.id)
        if fresh:
            profile = fresh
            st.session_state.profile = fresh

        section_header("Identity", "These fields can only be updated by an administrator")
        c1, c2 = st.columns(2)
        c1.markdown(f"**First Name:** {profile.get('first_name','—') or '—'}")
        c2.markdown(f"**Last Name:** {profile.get('last_name','—') or '—'}")
        c1.markdown(f"**Employee ID:** {profile.get('employee_id','—') or '—'}")
        c2.markdown(f"**Email:** {user.email}")

        st.divider()
        section_header("Profile Details", "Update your contact and academic information")

        with st.form("faculty_profile_form"):
            c1, c2         = st.columns(2)
            phone          = c1.text_input("Phone Number",
                                            value=profile.get("phone","") or "")
            office         = c2.text_input("Office Location",
                                            value=profile.get("office_location","") or "")
            qualification  = c1.text_input("Qualification (e.g. PhD, MSc)",
                                            value=profile.get("qualification","") or "")
            specialization = c2.text_input("Specialization / Subject Area",
                                            value=profile.get("specialization","") or "")
            address        = st.text_input("Address",
                                            value=profile.get("address","") or "")
            publications   = st.text_area("Publications",
                                           value=profile.get("publications","") or "",
                                           height=100)
            submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

        if submitted:
            updates = {
                "phone":           phone.strip(),
                "office_location": office.strip(),
                "qualification":   qualification.strip(),
                "specialization":  specialization.strip(),
                "address":         address.strip(),
                "publications":    publications.strip(),
            }
            with st.spinner("Saving..."):
                ok = ProfileService.update_profile(user.id, updates)
            if ok:
                st.session_state.profile.update(updates)
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
