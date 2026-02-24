import streamlit as st
from core.layout import base_console
from core.guards import require_role, require_approval
from services.faculty_service import FacultyService
from services.course_service import CourseService
from services.semester_service import SemesterService
from ui.styles import section_header
from ui.dashboard import render_dashboard


@require_role(["faculty"])
def faculty_console() -> None:

    user    = st.session_state.user
    profile = FacultyService.get_profile(user.id)

    require_approval(profile)

    if not profile:
        st.error("Your profile could not be loaded. Please contact support.")
        return

    # Keep session profile fresh
    st.session_state.profile = profile

    menu = base_console(
        "Faculty Panel",
        [
            "📊 Dashboard",
            "📚 My Courses",
            "👤 My Profile",
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

        sems = SemesterService.get_all()
        active_sem = SemesterService.get_active()

        if sems:
            sem_map = {s["name"]: s["id"] for s in sems}
            sem_names = list(sem_map.keys())
            default = active_sem["name"] if active_sem and active_sem["name"] in sem_names else sem_names[0]
            sel_sem_name = st.selectbox("Semester", sem_names,
                                        index=sem_names.index(default),
                                        key="faculty_sem_filter")
            sel_sem_id = sem_map[sel_sem_name]
        else:
            sel_sem_id = None

        with st.spinner("Loading courses..."):
            assignments = CourseService.get_faculty_courses(user.id, sel_sem_id)

        if not assignments:
            st.info("No courses assigned to you for this semester.")
        else:
            section_header(f"Assigned Courses", f"{len(assignments)} course(s)")
            for a in assignments:
                course = a.get("courses", {})
                dept   = (course.get("departments") or {}).get("name", "—")
                enrolled = CourseService.get_enrollment_count(course["id"])

                with st.expander(
                    f"📘 {course.get('code','—')} — {course.get('name','—')} "
                    f"| {dept} | {enrolled} students enrolled"
                ):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Credits",      course.get("credits", "—"))
                    col2.metric("Max Students", course.get("max_students", "—"))
                    col3.metric("Enrolled",     enrolled)

                    if course.get("description"):
                        st.markdown(f"**Description:** {course['description']}")

    # ==============================================================
    # MY PROFILE
    # ==============================================================
    elif menu == "👤 My Profile":
        st.title("👤 My Profile")

        col1, col2 = st.columns(2)
        col1.markdown(f"**Email:** {st.session_state.user.email}")
        col2.markdown(f"**Role:** Faculty")

        st.divider()

        with st.form("profile_form"):
            section_header("Update Profile")
            c1, c2 = st.columns(2)
            first = c1.text_input("First Name", value=profile.get("first_name", ""))
            last  = c2.text_input("Last Name",  value=profile.get("last_name", ""))
            submitted = st.form_submit_button("Save Changes", use_container_width=True)

        if submitted:
            if not first.strip() and not last.strip():
                st.warning("Please enter at least a first or last name.")
            else:
                success = FacultyService.update_profile(
                    user.id,
                    {"first_name": first.strip(), "last_name": last.strip()}
                )
                if success:
                    st.success("Profile updated successfully.")
                    st.rerun()
                else:
                    st.error("Update failed. Please try again.")
