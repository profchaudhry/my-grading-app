import streamlit as st
from core.layout import base_console
from core.guards import require_role
from services.profile_service import ProfileService
from services.enrollment_service import EnrollmentService
from ui.dashboard import render_dashboard
from ui.components import render_change_password
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
                course  = e.get("courses", {}) or {}
                dept    = (course.get("departments") or {}).get("name", "—")
                sem     = (e.get("semesters") or {}).get("name", "—")
                with st.expander(
                    f"📘 **{course.get('code','—')}** — {course.get('name','—')} | {sem}"
                ):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Department:** {dept}")
                    c2.markdown(f"**Credits:** {course.get('credits','—')}")
                    c3.markdown(f"**Semester:** {sem}")
                    if course.get("description"):
                        st.markdown(f"**Description:** {course['description']}")

    # ==============================================================
    # MY PROFILE
    # ==============================================================
    elif menu == "👤 My Profile":
        st.title("👤 My Profile")

        # Always fetch fresh profile
        fresh = ProfileService.get_profile(user.id)
        if fresh:
            profile = fresh
            st.session_state.profile = fresh

        st.divider()

        # ── Read-only credentials ──
        section_header("Personal Information", "Contact your administrator to update these fields")

        c1, c2 = st.columns(2)
        c1.markdown(f"**First Name:** {profile.get('first_name','—') or '—'}")
        c2.markdown(f"**Last Name:** {profile.get('last_name','—') or '—'}")
        c1.markdown(f"**Enrollment Number:** {profile.get('enrollment_number','—') or '—'}")
        c2.markdown(f"**Student ID:** {profile.get('student_id','—') or '—'}")
        c1.markdown(f"**Program:** {profile.get('program','—') or '—'}")
        c2.markdown(f"**Year of Study:** {profile.get('year_of_study','—') or '—'}")
        c1.markdown(f"**Date of Birth:** {profile.get('date_of_birth','—') or '—'}")

        st.divider()

        # ── Editable fields ──
        section_header("Contact Information", "You can update these fields")

        with st.form("student_profile_form"):
            email_val = st.text_input(
                "Email Address",
                value=user.email,
                disabled=True,         # email is auth-managed, shown for info
                help="Contact admin to change your email address."
            )
            phone = st.text_input(
                "Phone Number",
                value=profile.get("phone","") or "",
                placeholder="e.g. +1 234 567 8900"
            )
            submitted = st.form_submit_button("Save Changes", use_container_width=True)

        if submitted:
            if ProfileService.update_profile(user.id, {"phone": phone.strip()}):
                st.success("Profile updated successfully.")
                st.session_state.profile["phone"] = phone.strip()
                st.rerun()
            else:
                st.error("Update failed. Please try again.")

    # ==============================================================
    # CHANGE PASSWORD
    # ==============================================================
    elif menu == "🔒 Change Password":
        st.title("🔒 Change Password")
        st.divider()
        render_change_password()
