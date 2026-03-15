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
        _render_student_syndicate(user, profile)

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


# ── Student Syndicate UI ─────────────────────────────────────────

def _pname_profile(p: dict) -> str:
    if not p:
        return "—"
    full = (p.get("full_name") or "").strip()
    if full:
        return full
    return f"{p.get('first_name','') or ''} {p.get('last_name','') or ''}".strip() or "—"


def _render_student_syndicate(user, profile):
    import datetime as _dt

    enrollments = EnrollmentService.get_student_enrollments(user.id)
    if not enrollments:
        st.info("You are not enrolled in any courses.")
        return

    course_map = {
        f"{e['courses']['code']} — {e['courses']['name']}": e["courses"]
        for e in enrollments if e.get("courses")
    }
    if not course_map:
        st.info("No courses available.")
        return

    sel_label   = st.selectbox("Select Course", list(course_map.keys()), key="syn_course_sel")
    course      = course_map[sel_label]
    course_uuid = course["id"]

    # ── Load config & state ──────────────────────────────────
    syn_cfg      = UProService.get_syndicate_config(course_uuid)
    max_members  = syn_cfg["max_syndicate_members"]
    join_open    = UProService.is_join_open(course_uuid)
    deadline_str = syn_cfg.get("syndicate_join_deadline")

    all_enrollments  = EnrollmentService.get_course_enrollments(course_uuid)
    enrolled_count   = len(all_enrollments)
    max_syndicates   = UProService.get_allowed_syndicate_count(course_uuid, enrolled_count)
    all_syndicates   = [s for s in UProService.get_syndicates(course_uuid)
                        if s.get("status") == "confirmed"]
    membership       = UProService.get_student_syndicate(course_uuid, user.id)

    # ── Status bar ───────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Max Members / Syndicate", max_members)
    c2.metric("Allowed Syndicates", max_syndicates)
    if deadline_str:
        try:
            dl = _dt.date.fromisoformat(str(deadline_str))
            days_left = (dl - _dt.date.today()).days
            c3.metric("Join Deadline", str(dl),
                       delta=f"{days_left}d left" if days_left >= 0 else "Closed",
                       delta_color="normal" if days_left >= 0 else "inverse")
        except Exception:
            c3.metric("Join Deadline", deadline_str)
    else:
        c3.metric("Join Deadline", "Not set")

    if not join_open:
        st.warning("⏰ The syndicate joining period has ended. Only admin/faculty can make changes.")
    else:
        st.success("✅ Syndicate joining is open.")

    st.divider()

    # ── CASE 1: Student is already in a syndicate ────────────
    if membership:
        syn     = membership.get("syndicates", {}) or {}
        syn_id  = membership["syndicate_id"]
        members = UProService.get_syndicate_members(syn_id)
        lead_id = syn.get("lead_student_id")

        section_header(
            f"🏷️ {syn.get('name','—')}",
            f"{len(members)} / {max_members} members"
        )

        # Member list
        for m in members:
            mp      = m.get("profiles", {}) or {}
            is_lead = mp.get("id") == lead_id
            st.markdown(
                f"{'👑 ' if is_lead else '👤 '}"
                f"**{_pname_profile(mp)}** "
                f"`{mp.get('enrollment_number','')}`"
                + (" *(Lead)*" if is_lead else "")
            )

        st.divider()

        # ── Voting (only after deadline) ─────────────────────
        if not join_open:
            _render_vote_section(course_uuid, syn_id, user.id, members, lead_id)

        # ── Leave syndicate (only before deadline) ────────────
        if join_open:
            st.divider()
            if st.button("🚪 Leave Syndicate", key="stu_leave_syn", type="secondary"):
                st.session_state["stu_leave_confirm"] = True

            if st.session_state.get("stu_leave_confirm"):
                st.warning("⚠️ Are you sure you want to leave this syndicate?")
                cy, cn = st.columns(2)
                if cy.button("Yes, leave", key="stu_leave_yes", use_container_width=True):
                    if UProService.remove_member(syn_id, user.id):
                        st.session_state.pop("stu_leave_confirm", None)
                        st.success("You have left the syndicate.")
                        st.rerun()
                    else:
                        st.error("Failed to leave.")
                if cn.button("Cancel", key="stu_leave_no", use_container_width=True):
                    st.session_state.pop("stu_leave_confirm", None)
                    st.rerun()

    # ── CASE 2: Not in any syndicate ─────────────────────────
    else:
        if not join_open:
            st.info("The joining period has ended and you are not in a syndicate. Contact your admin or faculty.")
            return

        st.info("You are not in any syndicate for this course yet.")

        tab_create, tab_join = st.tabs(["➕ Create Syndicate", "🔍 Join Syndicate"])

        # ── CREATE ────────────────────────────────────────────
        with tab_create:
            section_header("Create a New Syndicate",
                            "Submit a name — admin/faculty will confirm it")
            # Check slot availability
            if len(all_syndicates) >= max_syndicates:
                st.error(
                    f"Maximum number of syndicates ({max_syndicates}) for this course "
                    f"has been reached. Please join an existing one."
                )
            else:
                syn_name_in = st.text_input(
                    "Syndicate Name", placeholder="e.g. Alpha Team",
                    key="stu_create_syn_name"
                )
                st.caption(
                    f"ℹ️ {max_syndicates - len(all_syndicates)} syndicate slot(s) remaining. "
                    f"Max {max_members} members each."
                )
                if st.button("🚀 Submit Syndicate", key="stu_create_syn_btn",
                             use_container_width=True, type="primary"):
                    name = syn_name_in.strip()
                    if not name:
                        st.error("Please enter a syndicate name.")
                    elif any(s["name"].lower() == name.lower() for s in all_syndicates):
                        st.error("A syndicate with this name already exists.")
                    else:
                        result = UProService.create_syndicate(
                            course_uuid, name,
                            lead_student_id=user.id,   # creator is initial lead
                            created_by_role="student",
                            status="confirmed",         # auto-confirmed; admin can rename
                        )
                        if result:
                            UProService.add_member(result["id"], course_uuid, user.id)  # creator always added
                            st.success(
                                f"✅ Syndicate **{name}** created! "
                                "Admin/faculty may edit the name. Others can now join."
                            )
                            st.rerun()
                        else:
                            st.error("❌ Failed. Name may already exist.")

        # ── JOIN ──────────────────────────────────────────────
        with tab_join:
            section_header("Join an Existing Syndicate",
                            "Pick a syndicate that has open spots")
            if not all_syndicates:
                st.info("No syndicates created yet for this course.")
            else:
                open_syns = []
                for s in all_syndicates:
                    mems = UProService.get_syndicate_members(s["id"])
                    if len(mems) < max_members:
                        open_syns.append((s, mems))

                if not open_syns:
                    st.warning("All syndicates are full. Ask admin/faculty to adjust limits.")
                else:
                    for syn, mems in open_syns:
                        lead_p  = syn.get("profiles") or {}
                        spots   = max_members - len(mems)
                        with st.expander(
                            f"🏷️ **{syn['name']}** — "
                            f"{len(mems)}/{max_members} members | {spots} spot(s) open"
                        ):
                            for m in mems:
                                mp      = m.get("profiles", {}) or {}
                                is_lead = mp.get("id") == syn.get("lead_student_id")
                                st.caption(
                                    f"{'👑 ' if is_lead else '👤 '}"
                                    f"{_pname_profile(mp)} "
                                    f"`{mp.get('enrollment_number','')}`"
                                )
                            if st.button(f"➕ Join {syn['name']}", key=f"stu_join_{syn['id']}",
                                         use_container_width=True, type="primary"):
                                _ok, _msg = UProService.add_member(syn["id"], course_uuid, user.id)
                                if _ok:
                                    st.success(f"✅ You have joined **{syn['name']}**!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {_msg}")


def _render_vote_section(course_uuid, syndicate_id, voter_id, members, current_lead_id):
    """Voting for syndicate lead — available after join deadline."""
    section_header("🗳️ Vote for Lead",
                    "Joining period ended — vote for your syndicate lead")
    existing_vote = UProService.get_student_vote(syndicate_id, voter_id)
    if existing_vote:
        st.info(f"✅ You already voted. Your vote: nominee ID `{existing_vote.get('nominee_id','—')}`")
        return

    member_profiles = [m.get("profiles", {}) or {} for m in members]
    eligible        = [p for p in member_profiles if p.get("id")]
    if not eligible:
        st.caption("No members to vote for.")
        return

    options     = {_pname_profile(p): p["id"] for p in eligible}
    sel_nominee = st.selectbox("Select nominee", list(options.keys()), key=f"vote_sel_{syndicate_id}")
    if st.button("🗳️ Cast Vote", key=f"vote_btn_{syndicate_id}",
                 use_container_width=True, type="primary"):
        ok, msg = UProService.submit_vote(course_uuid, voter_id,
                                          syndicate_id, options[sel_nominee])
        if ok:
            st.success(f"✅ Vote cast for {sel_nominee}. Lead updated by majority.")
            st.rerun()
        else:
            st.error(f"❌ {msg}")


# ── Profile change request helpers ──────────────────────────────── ───────────────────────────────

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
