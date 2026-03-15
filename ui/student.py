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
from services.profile_request_service import ProfileRequestService
from ui.styles import section_header
import re as _re

_STATUS_ICON = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
_FIELD_LABEL = {"date_of_birth": "Date of Birth", "personal_email": "Personal Email"}


@require_role(["student"])
def student_console() -> None:

    user    = st.session_state.user
    profile = st.session_state.get("profile") or {}
    role    = st.session_state.get("role") or "student"

    menu = base_console(
        "Student Panel",
        [
            "📊 Dashboard",
            "📚 My Courses",
            "📋 Announcements",
            "📊 My Grades",
            "📄 My Transcript",
            "🏷️ My Syndicate",
            "👤 My Profile",
            "🔒 Change Password",
        ]
    )

    if menu == "📊 Dashboard":
        render_dashboard()

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

    elif menu == "📋 Announcements":
        enrolled = [
            e["course_id"] for e in (
                supabase.table("enrollments")
                .select("course_id")
                .eq("student_id", user.id)
                .eq("status", "active")
                .execute().data or []
            )
        ]
        render_student_announcements(user.id, role, enrolled)

    elif menu == "📊 My Grades":
        st.title("📊 My Grades")
        grades = GradingService.get_student_grades(user.id)
        if not grades:
            st.info("No grades have been released yet.")
        else:
            gpa_vals = [g["gpa_points"] for g in grades if g.get("gpa_points") is not None]
            cgpa = round(sum(gpa_vals) / len(gpa_vals), 2) if gpa_vals else None
            c1, c2 = st.columns(2)
            c1.metric("Courses with Released Grades", len(grades))
            if cgpa is not None:
                c2.metric("CGPA", cgpa)
            st.divider()
            section_header("Course Grades")
            grade_colours = {
                "A": "🟢", "A-": "🟢", "B+": "🔵", "B": "🔵", "B-": "🔵",
                "C+": "🟡", "C": "🟡", "C-": "🟡", "D+": "🟠", "D": "🟠", "F": "🔴",
            }
            for g in grades:
                course = g.get("courses", {}) or {}
                letter = g.get("letter_grade") or "—"
                total  = g.get("total_score")
                icon   = grade_colours.get(letter, "⚪")
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

    elif menu == "📄 My Transcript":
        render_student_reports(user.id)

    elif menu == "🏷️ My Syndicate":
        st.title("🏷️ My Syndicate")
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
            membership  = UProService.get_student_syndicate(course_uuid, user.id)
            if membership:
                syn    = membership.get("syndicates", {}) or {}
                status = syn.get("status", "—")
                status_icons = {"confirmed": "✅", "pending": "⏳", "rejected": "❌"}
                st.info(
                    f"You are in syndicate: **{syn.get('name','—')}** | "
                    f"Status: {status_icons.get(status,'')} {status.capitalize()}"
                )
                members = UProService.get_syndicate_members(membership["syndicate_id"])
                if members:
                    section_header("Syndicate Members")
                    for m in members:
                        mp      = m.get("profiles", {}) or {}
                        is_lead = mp.get("id") == syn.get("lead_student_id")
                        st.caption(
                            f"{'👑 Lead: ' if is_lead else '👤 '}"
                            f"{(mp.get('full_name') or mp.get('first_name',''))} "
                            f"`{mp.get('enrollment_number','')}`"
                        )
            else:
                st.warning("You are not in a syndicate for this course yet.")
                st.divider()
                section_header("Submit Syndicate Details",
                                "Submit your syndicate name and lead for faculty confirmation")
                with st.form("submit_syndicate_form"):
                    syn_name  = st.text_input("Syndicate Name", placeholder="e.g. Alpha Team")
                    lead_name = st.text_input("Syndicate Lead Name",
                                              placeholder="Full name of the syndicate lead")
                    st.caption("Your submission will be reviewed and confirmed by faculty.")
                    submitted = st.form_submit_button("Submit Syndicate", use_container_width=True)
                if submitted:
                    if not syn_name or not lead_name:
                        st.error("Both syndicate name and lead name are required.")
                    else:
                        enrolled_list = EnrollmentService.get_course_enrollments(course_uuid)
                        lead_profile  = None
                        for e in enrolled_list:
                            p     = e.get("profiles", {}) or {}
                            pname = (p.get("full_name") or
                                     f"{p.get('first_name','')} {p.get('last_name','')}").strip().lower()
                            if pname == lead_name.strip().lower():
                                lead_profile = p
                                break
                        result = UProService.create_syndicate(
                            course_uuid, syn_name,
                            lead_student_id=lead_profile["id"] if lead_profile else None,
                            created_by_role="student", status="pending",
                        )
                        if result:
                            UProService.add_member(result["id"], course_uuid, user.id)
                            st.success("✅ Syndicate submitted! It will appear here once faculty confirms it.")
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

        # ── Read-only identity ────────────────────────────────
        section_header("Personal Information",
                        "Contact your administrator to update name, enrollment or program")
        c1, c2 = st.columns(2)
        display_name = profile.get("full_name", "").strip() or \
                       f"{profile.get('first_name','') or ''} {profile.get('last_name','') or ''}".strip()
        c1.markdown(f"**Full Name:** {display_name or '—'}")
        c2.markdown(f"**Enrollment Number:** {profile.get('enrollment_number','—') or '—'}")
        c1.markdown(f"**Program:** {profile.get('program','—') or '—'}")
        c2.markdown(f"**Year of Study:** {profile.get('year_of_study','—') or '—'}")
        c1.markdown(f"**Login Email:** {user.email}")
        c2.markdown(f"**Personal Email:** {profile.get('personal_email','—') or '—'}")

        st.divider()

        # ── Editable contact info ─────────────────────────────
        section_header("Contact Information", "Phone and address can be updated directly")
        p_phone = st.text_input("Phone Number", value=profile.get("phone","") or "",
                                placeholder="e.g. +92 300 1234567", key="stu_phone")
        p_addr  = st.text_input("Address",      value=profile.get("address","") or "",
                                placeholder="e.g. 123 Main St, City",   key="stu_addr")
        if st.button("💾 Save Contact Info", key="stu_contact_save",
                     use_container_width=True, type="primary"):
            ok = ProfileService.update_profile(user.id, {
                "phone": p_phone.strip(), "address": p_addr.strip()
            })
            if ok:
                st.session_state.profile["phone"]   = p_phone.strip()
                st.session_state.profile["address"] = p_addr.strip()
                st.success("✅ Contact info updated.")
                st.rerun()
            else:
                st.error("❌ Save failed.")

        st.divider()

        # ── Date of Birth ─────────────────────────────────────
        section_header("Date of Birth",
                        "Set once freely. After that, changes require admin approval.")
        current_dob = (profile.get("date_of_birth") or "").strip()
        if not current_dob:
            st.caption("📝 Not set yet — enter below to save for the first time.")
            dob_input = st.text_input("Date of Birth (YYYY-MM-DD)", value="",
                                       placeholder="e.g. 2000-05-15", key="stu_dob_first")
            if st.button("💾 Save Date of Birth", key="stu_dob_save_first", use_container_width=True):
                dob_val = dob_input.strip()
                if not dob_val:
                    st.error("Please enter a date.")
                elif not _re.match(r"^\d{4}-\d{2}-\d{2}$", dob_val):
                    st.error("Use format YYYY-MM-DD, e.g. 2000-05-15")
                else:
                    ok = ProfileService.update_profile(user.id, {"date_of_birth": dob_val})
                    if ok:
                        st.success(f"✅ Date of birth saved as {dob_val}.")
                        st.rerun()
                    else:
                        st.error("❌ Save failed.")
        else:
            st.markdown(f"**Current:** `{current_dob}`")
            _render_change_request(
                user.id, "date_of_birth", current_dob,
                label="Date of Birth", placeholder="e.g. 2000-05-15",
                hint="Format: YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$",
            )

        st.divider()

        # ── Personal Email ────────────────────────────────────
        section_header("Personal Email",
                        "Set once freely. After that, changes require admin approval.")
        current_email = (profile.get("personal_email") or "").strip()
        if not current_email:
            st.caption("📝 Not set yet — enter below to save for the first time.")
            email_input = st.text_input("Personal Email", value="",
                                         placeholder="e.g. john@gmail.com", key="stu_pemail_first")
            if st.button("💾 Save Personal Email", key="stu_pemail_save_first", use_container_width=True):
                email_val = email_input.strip().lower()
                if not email_val or "@" not in email_val:
                    st.error("Please enter a valid email address.")
                else:
                    ok = ProfileService.update_profile(user.id, {"personal_email": email_val})
                    if ok:
                        st.success(f"✅ Personal email saved as {email_val}.")
                        st.rerun()
                    else:
                        st.error(
                            "❌ Save failed. If this is the first time, the admin may need to "
                            "add a `personal_email` column to the profiles table in Supabase."
                        )
        else:
            st.markdown(f"**Current:** `{current_email}`")
            _render_change_request(
                user.id, "personal_email", current_email,
                label="Personal Email", placeholder="e.g. john@gmail.com",
                hint="Must be a valid email", pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            )

        st.divider()

        # ── Request history ───────────────────────────────────
        _render_request_history(user.id)

    elif menu == "🔒 Change Password":
        st.title("🔒 Change Password")
        st.divider()
        render_change_password()


# ── Profile change request helpers ───────────────────────────────

def _render_change_request(student_id, field_name, current_value,
                            label, placeholder, hint, pattern):
    """Show 'request a change' UI for a locked field."""
    requests = ProfileRequestService.get_student_requests(student_id)
    pending  = next(
        (r for r in requests
         if r["field_name"] == field_name and r["status"] == "pending"),
        None
    )
    if pending:
        st.info(
            f"⏳ Pending change request: `{pending['new_value']}` — "
            "waiting for admin approval."
        )
        return

    with st.expander(f"✏️ Request change to {label}", expanded=False):
        new_val = st.text_input(f"New {label}", value="", placeholder=placeholder,
                                key=f"req_{field_name}_input")
        st.caption(f"ℹ️ {hint}. An admin will review before applying the change.")
        if st.button("📤 Submit Change Request", key=f"req_{field_name}_btn",
                     use_container_width=True):
            val = new_val.strip()
            if not val:
                st.error("Please enter a new value.")
            elif val == current_value:
                st.error("New value is the same as current.")
            elif not _re.match(pattern, val):
                st.error(f"Invalid format. {hint}.")
            else:
                ok, msg = ProfileRequestService.submit_request(
                    student_id, field_name, val, current_value
                )
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")


def _render_request_history(student_id):
    """Show student's own change request history."""
    section_header("My Change Requests", "History of your profile update requests")
    requests = ProfileRequestService.get_student_requests(student_id)
    if not requests:
        st.caption("No change requests submitted yet.")
        return
    for req in requests:
        status  = req.get("status", "pending")
        icon    = _STATUS_ICON.get(status, "❓")
        label   = _FIELD_LABEL.get(req.get("field_name", ""), req.get("field_name", "—"))
        created = (req.get("created_at") or "")[:10]
        with st.expander(
            f"{icon} **{label}** → `{req.get('new_value','—')}` — "
            f"{status.capitalize()} ({created})"
        ):
            c1, c2 = st.columns(2)
            c1.markdown(f"**Field:** {label}")
            c2.markdown(f"**Status:** {icon} {status.capitalize()}")
            c1.markdown(f"**Requested:** `{req.get('new_value','—')}`")
            c2.markdown(f"**Was:** `{req.get('old_value','—') or '—'}`")
            if req.get("admin_note"):
                st.caption(f"Admin note: {req['admin_note']}")
