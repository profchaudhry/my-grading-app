"""
UPro Grade UI — used by faculty_ultra and admin consoles.
Tabs: Syndicates | UPro Scores | AOL Gradebook | AOL Config
"""
import streamlit as st
import pandas as pd
import json
from services.upro_service import UProService
from services.grading_service import GradingService, score_to_letter, suggest_grade_change
from services.enrollment_service import EnrollmentService
from ui.styles import section_header


# ── Helpers ───────────────────────────────────────────────────────

def _pname(p: dict) -> str:
    if not p:
        return "—"
    full = (p.get("full_name") or "").strip()
    if full:
        return full
    return f"{p.get('first_name','')} {p.get('last_name','')}".strip() or "—"


def _grade_icon(letter: str) -> str:
    if not letter:
        return "⚪"
    if letter.startswith("A"):  return "🟢"
    if letter.startswith("B"):  return "🔵"
    if letter.startswith("C"):  return "🟡"
    if letter.startswith("D"):  return "🟠"
    return "🔴"


# ── Main renderer ─────────────────────────────────────────────────

def render_upro_grade(course_uuid: str, course_info: dict, is_admin: bool = False) -> None:
    scheme   = GradingService.get_effective_scheme(course_uuid)
    max_quiz = float(scheme["weight_quiz"])
    max_asgn = float(scheme["weight_assignment"])
    max_mid  = float(scheme["weight_midterm"])
    max_fin  = float(scheme["weight_final"])

    enrollments = EnrollmentService.get_course_enrollments(course_uuid)
    if not enrollments:
        st.warning("No students enrolled in this course.")
        return

    enrolled_profiles = [e["profiles"] for e in enrollments if e.get("profiles")]
    student_map = {_pname(p): p for p in enrolled_profiles}

    tab_syn, tab_scores, tab_aol, tab_cfg = st.tabs([
        "👥 Syndicates",
        "📝 UPro Scores",
        "📊 AOL Gradebook",
        "⚙️ AOL Config",
    ])

    # ══════════════════════════════════════════════════════════════
    # TAB 1 — SYNDICATES
    # ══════════════════════════════════════════════════════════════
    with tab_syn:
        _render_syndicates(course_uuid, enrolled_profiles, student_map, is_admin)

    # ══════════════════════════════════════════════════════════════
    # TAB 2 — UPRO SCORES
    # ══════════════════════════════════════════════════════════════
    with tab_scores:
        _render_upro_scores(
            course_uuid, enrolled_profiles,
            max_quiz, max_asgn, max_mid, max_fin
        )

    # ══════════════════════════════════════════════════════════════
    # TAB 3 — AOL GRADEBOOK
    # ══════════════════════════════════════════════════════════════
    with tab_aol:
        _render_aol_gradebook(course_uuid, course_info, scheme, is_admin)

    # ══════════════════════════════════════════════════════════════
    # TAB 4 — AOL CONFIG
    # ══════════════════════════════════════════════════════════════
    with tab_cfg:
        _render_aol_config(course_uuid)


# ── SYNDICATES ────────────────────────────────────────────────────

def _render_syndicates(course_uuid, enrolled_profiles, student_map, is_admin):
    st.subheader("👥 Syndicate Management")

    syndicates = UProService.get_syndicates(course_uuid)

    # ── Pending submissions (from students) ────────────────────
    pending = [s for s in syndicates if s["status"] == "pending"]
    if pending:
        section_header("⏳ Pending Student Submissions", f"{len(pending)} awaiting confirmation")
        for syn in pending:
            lead_p  = syn.get("profiles") or {}
            lead_nm = _pname(lead_p) if lead_p else "—"
            members = UProService.get_syndicate_members(syn["id"])
            with st.expander(f"📋 **{syn['name']}** — Lead: {lead_nm} | {len(members)} member(s)"):
                st.caption(f"Submitted by student | Members: {', '.join(_pname(m.get('profiles',{})) for m in members)}")
                c1, c2 = st.columns(2)
                if c1.button("✅ Confirm", key=f"confirm_syn_{syn['id']}", use_container_width=True):
                    if UProService.confirm_syndicate(syn["id"]):
                        st.success("Confirmed.")
                        st.rerun()
                if c2.button("❌ Reject",  key=f"reject_syn_{syn['id']}", use_container_width=True):
                    if UProService.reject_syndicate(syn["id"]):
                        st.warning("Rejected.")
                        st.rerun()
        st.divider()

    # ── Create new syndicate ───────────────────────────────────
    with st.expander("➕ Create New Syndicate", expanded=False):
        with st.form("create_syn_form"):
            syn_name = st.text_input("Syndicate Name", placeholder="e.g. Alpha Team")
            lead_label = st.selectbox(
                "Syndicate Lead (enrolled student)",
                ["— None —"] + list(student_map.keys()),
                key="syn_lead_sel"
            )
            if st.form_submit_button("Create Syndicate", use_container_width=True):
                if not syn_name:
                    st.error("Syndicate name is required.")
                else:
                    lead_id = student_map[lead_label]["id"] if lead_label != "— None —" else None
                    result  = UProService.create_syndicate(
                        course_uuid, syn_name, lead_id,
                        created_by_role="admin" if is_admin else "faculty_ultra",
                        status="confirmed"
                    )
                    if result:
                        st.success(f"✅ Syndicate '{syn_name}' created.")
                        st.rerun()
                    else:
                        st.error("❌ Failed. Name may already exist.")

    st.divider()

    # ── Confirmed syndicates ───────────────────────────────────
    confirmed = [s for s in syndicates if s["status"] == "confirmed"]
    section_header("✅ Confirmed Syndicates", f"{len(confirmed)}")

    # Track which students are already assigned
    assigned_student_ids: set[str] = set()
    for syn in confirmed:
        for m in UProService.get_syndicate_members(syn["id"]):
            assigned_student_ids.add(m["student_id"])

    if not confirmed:
        st.info("No confirmed syndicates yet.")
    else:
        for syn in confirmed:
            members = UProService.get_syndicate_members(syn["id"])
            lead_p  = syn.get("profiles") or {}
            with st.expander(
                f"🏷️ **{syn['name']}** | Lead: {_pname(lead_p) or '—'} | {len(members)} member(s)"
            ):
                # Member list
                if members:
                    for m in members:
                        mp = m.get("profiles", {}) or {}
                        c1, c2 = st.columns([6,1])
                        is_lead = mp.get("id") == syn.get("lead_student_id")
                        c1.markdown(
                            f"{'👑 ' if is_lead else '👤 '}"
                            f"**{_pname(mp)}** `{mp.get('enrollment_number','')}`"
                            + (" *(Lead)*" if is_lead else "")
                        )
                        if c2.button("Remove", key=f"rm_mem_{syn['id']}_{mp.get('id')}"):
                            UProService.remove_member(syn["id"], mp["id"])
                            st.rerun()
                else:
                    st.caption("No members yet.")

                st.divider()
                # Add members
                available = [
                    p for p in enrolled_profiles
                    if p["id"] not in {m["student_id"] for m in members}
                ]
                if available:
                    with st.form(f"add_mem_{syn['id']}"):
                        add_sel = st.selectbox(
                            "Add Student",
                            [_pname(p) for p in available],
                            key=f"add_mem_sel_{syn['id']}"
                        )
                        if st.form_submit_button("➕ Add Member", use_container_width=True):
                            target = next(p for p in available if _pname(p) == add_sel)
                            if UProService.add_member(syn["id"], course_uuid, target["id"]):
                                st.success(f"✅ {add_sel} added.")
                                st.rerun()
                            else:
                                st.error("Failed. Student may already be in another syndicate.")

                # Edit lead
                with st.form(f"edit_lead_{syn['id']}"):
                    member_profiles = [m.get("profiles",{}) for m in members]
                    if member_profiles:
                        lead_options = [_pname(p) for p in member_profiles]
                        current_lead = next(
                            (i for i, p in enumerate(member_profiles)
                             if p.get("id") == syn.get("lead_student_id")), 0
                        )
                        new_lead_sel = st.selectbox("Change Lead", lead_options,
                                                     index=current_lead, key=f"cl_{syn['id']}")
                        if st.form_submit_button("Update Lead"):
                            new_lead = next(p for p in member_profiles if _pname(p) == new_lead_sel)
                            UProService.update_syndicate(syn["id"], {"lead_student_id": new_lead["id"]})
                            st.success("Lead updated.")
                            st.rerun()

                # Delete syndicate
                st.divider()
                if st.button("🗑️ Delete Syndicate", key=f"del_syn_{syn['id']}",
                              type="secondary"):
                    UProService.delete_syndicate(syn["id"])
                    st.rerun()

    # ── Unassigned students ────────────────────────────────────
    unassigned = [p for p in enrolled_profiles if p["id"] not in assigned_student_ids]
    if unassigned:
        st.divider()
        section_header("⚠️ Unassigned Students", f"{len(unassigned)} not in any syndicate")
        for p in unassigned:
            st.caption(f"• {_pname(p)} `{p.get('enrollment_number','')}`")


# ── UPRO SCORES ───────────────────────────────────────────────────

def _render_upro_scores(course_uuid, enrolled_profiles, max_quiz, max_asgn, max_mid, max_fin):
    st.subheader("📝 UPro Score Entry")
    st.caption(
        f"Max marks from grading scheme — "
        f"Quiz: **{max_quiz}** | Assignment: **{max_asgn}** | "
        f"Midterm: **{max_mid}** | Final: **{max_fin}**"
    )

    syndicates = [s for s in UProService.get_syndicates(course_uuid)
                  if s["status"] == "confirmed"]

    if not syndicates:
        st.warning("No confirmed syndicates yet. Set up syndicates first.")
        return

    tab_asgn_sc, tab_quiz_sc, tab_mid_sc, tab_fin_sc = st.tabs([
        "📄 Assignments", "📝 Quizzes", "📘 Midterm", "📗 Final"
    ])

    # ── Assignments (group entry, individual edit) ─────────────
    with tab_asgn_sc:
        section_header("Assignment Scores",
                        "Enter group score — auto-fills all members, edit individually")
        syn_labels = [s["name"] for s in syndicates]
        sel_syn_name = st.selectbox("Select Syndicate", syn_labels, key="upro_asgn_syn")
        sel_syn = next(s for s in syndicates if s["name"] == sel_syn_name)
        members = UProService.get_syndicate_members(sel_syn["id"])

        if not members:
            st.info("No members in this syndicate.")
        else:
            # Group apply — store applied value in session_state keyed to syndicate
            _asgn_grp_key = f"upro_asgn_grp_{sel_syn['id']}"
            group_val = st.number_input(
                f"Group Assignment Score (out of {max_asgn})",
                min_value=0.0, max_value=max_asgn,
                value=0.0, step=0.5, key="upro_asgn_group"
            )
            if st.button("Apply to all members ↓", key="upro_asgn_apply"):
                st.session_state[_asgn_grp_key] = group_val
                st.rerun()

            st.divider()
            # Individual inputs — no st.form, so Apply rerun takes effect immediately
            entries = {}
            for m in members:
                mp  = m.get("profiles", {}) or {}
                sid = mp["id"]
                existing    = UProService.get_student_upro_score(course_uuid, sid)
                # Use group value if Apply was clicked, else existing DB value, else 0
                if _asgn_grp_key in st.session_state:
                    default_val = float(st.session_state[_asgn_grp_key])
                elif existing and existing.get("assignment_score") is not None:
                    default_val = float(existing["assignment_score"])
                else:
                    default_val = 0.0
                default_val = min(default_val, max_asgn)
                is_lead = sid == sel_syn.get("lead_student_id")
                entries[sid] = st.number_input(
                    f"{'👑 ' if is_lead else ''}{_pname(mp)} "
                    f"`{mp.get('enrollment_number','')}`",
                    min_value=0.0, max_value=max_asgn,
                    value=default_val, step=0.5,
                    key=f"upro_asgn_{sid}"
                )
            if st.button("💾 Save Assignment Scores", key="upro_asgn_save",
                         use_container_width=True, type="primary"):
                all_ok = True
                for sid, val in entries.items():
                    existing = UProService.get_student_upro_score(course_uuid, sid)
                    ok = UProService.save_upro_score(
                        course_uuid, sid,
                        syndicate_id=sel_syn["id"],
                        quiz_score=existing["quiz_score"] if existing else None,
                        assignment_score=val,
                        midterm_score=existing["midterm_score"] if existing else None,
                        final_score=existing["final_score"] if existing else None,
                    )
                    if not ok:
                        all_ok = False
                # Clear group state after saving
                st.session_state.pop(_asgn_grp_key, None)
                if all_ok:
                    st.success("✅ Assignment scores saved.")
                    st.rerun()
                else:
                    st.error("❌ Some saves failed.")

    # ── Quizzes (individual per member) ───────────────────────
    with tab_quiz_sc:
        section_header("Quiz Scores", "Individual score per student")
        syn_labels = [s["name"] for s in syndicates]
        sel_syn_name = st.selectbox("Select Syndicate", syn_labels, key="upro_quiz_syn")
        sel_syn = next(s for s in syndicates if s["name"] == sel_syn_name)
        members = UProService.get_syndicate_members(sel_syn["id"])

        if not members:
            st.info("No members in this syndicate.")
        else:
            with st.form("upro_quiz_form"):
                entries = {}
                for m in members:
                    mp  = m.get("profiles", {}) or {}
                    sid = mp["id"]
                    existing = UProService.get_student_upro_score(course_uuid, sid)
                    default_val = float(existing["quiz_score"]) \
                                  if existing and existing.get("quiz_score") is not None \
                                  else 0.0
                    is_lead = sid == sel_syn.get("lead_student_id")
                    entries[sid] = st.number_input(
                        f"{'👑 ' if is_lead else '👤 '}{_pname(mp)} "
                        f"`{mp.get('enrollment_number','')}`",
                        min_value=0.0, max_value=max_quiz,
                        value=default_val, step=0.5,
                        key=f"upro_quiz_{sid}"
                    )
                if st.form_submit_button("💾 Save Quiz Scores", use_container_width=True):
                    all_ok = True
                    for sid, val in entries.items():
                        existing = UProService.get_student_upro_score(course_uuid, sid)
                        ok = UProService.save_upro_score(
                            course_uuid, sid,
                            syndicate_id=sel_syn["id"],
                            quiz_score=val,
                            assignment_score=existing["assignment_score"] if existing else None,
                            midterm_score=existing["midterm_score"] if existing else None,
                            final_score=existing["final_score"] if existing else None,
                        )
                        if not ok:
                            all_ok = False
                    if all_ok:
                        st.success("✅ Quiz scores saved.")
                    else:
                        st.error("❌ Some saves failed.")

    # ── Midterm (individual) ───────────────────────────────────
    with tab_mid_sc:
        section_header("Midterm Scores", "Individual score per student")
        _render_individual_exam_scores(
            course_uuid, enrolled_profiles, syndicates,
            component="midterm", max_val=max_mid, key_prefix="mid"
        )

    # ── Final (individual) ────────────────────────────────────
    with tab_fin_sc:
        section_header("Final Scores", "Individual score per student")
        _render_individual_exam_scores(
            course_uuid, enrolled_profiles, syndicates,
            component="final", max_val=max_fin, key_prefix="fin"
        )


def _render_individual_exam_scores(course_uuid, enrolled_profiles, syndicates,
                                    component, max_val, key_prefix):
    entry_mode = st.radio(
        "Entry mode", ["📋 Table (all students)", "👤 Individual"],
        horizontal=True, key=f"{key_prefix}_mode"
    )

    if entry_mode == "📋 Table (all students)":
        rows = []
        existing_map = {}
        for p in enrolled_profiles:
            s = UProService.get_student_upro_score(course_uuid, p["id"])
            existing_map[p["id"]] = s
            rows.append({
                "student_id":     p["id"],
                "Name":           _pname(p),
                "Enrollment No":  p.get("enrollment_number","—"),
                "Score":          float(s[f"{component}_score"])
                                  if s and s.get(f"{component}_score") is not None
                                  else 0.0,
            })
        df = pd.DataFrame(rows)
        edited = st.data_editor(
            df[["Name","Enrollment No","Score"]],
            column_config={
                "Name":          st.column_config.TextColumn(disabled=True),
                "Enrollment No": st.column_config.TextColumn(disabled=True),
                "Score":         st.column_config.NumberColumn(
                                     f"Score (out of {max_val})",
                                     min_value=0.0, max_value=max_val, step=0.5),
            },
            use_container_width=True, hide_index=True,
            key=f"{key_prefix}_table"
        )
        if st.button(f"💾 Save All {component.title()} Scores",
                      use_container_width=True, type="primary",
                      key=f"save_{key_prefix}_table"):
            saved = 0
            for i, row in edited.iterrows():
                sid      = df.iloc[i]["student_id"]
                existing = existing_map.get(sid)
                syn_id   = existing["syndicate_id"] if existing else None
                ok = UProService.save_upro_score(
                    course_uuid, sid, syndicate_id=syn_id,
                    **{
                        "quiz_score":       existing["quiz_score"] if existing else None,
                        "assignment_score": existing["assignment_score"] if existing else None,
                        "midterm_score":    existing["midterm_score"] if existing else None,
                        "final_score":      existing["final_score"] if existing else None,
                        f"{component}_score": float(row["Score"]),
                    }
                )
                if ok:
                    saved += 1
            st.success(f"✅ Saved {saved} {component} score(s).")

    else:  # Individual
        sel_label = st.selectbox(
            "Select Student",
            [_pname(p) for p in enrolled_profiles],
            key=f"{key_prefix}_sel"
        )
        p        = next(pr for pr in enrolled_profiles if _pname(pr) == sel_label)
        sid      = p["id"]
        existing = UProService.get_student_upro_score(course_uuid, sid)
        default  = float(existing[f"{component}_score"]) \
                   if existing and existing.get(f"{component}_score") is not None else 0.0

        with st.form(f"{key_prefix}_ind_form"):
            val = st.number_input(
                f"{component.title()} Score for {_pname(p)} (out of {max_val})",
                min_value=0.0, max_value=max_val, value=default, step=0.5
            )
            if st.form_submit_button(f"💾 Save {component.title()} Score",
                                      use_container_width=True):
                syn_id = existing["syndicate_id"] if existing else None
                ok = UProService.save_upro_score(
                    course_uuid, sid, syndicate_id=syn_id,
                    quiz_score=existing["quiz_score"] if existing else None,
                    assignment_score=existing["assignment_score"] if existing else None,
                    midterm_score=existing["midterm_score"] if existing else None,
                    final_score=existing["final_score"] if existing else None,
                    **{f"{component}_score": val},
                )
                if ok:
                    st.success(f"✅ {component.title()} score saved for {_pname(p)}.")
                else:
                    st.error("❌ Save failed.")


# ── AOL GRADEBOOK ─────────────────────────────────────────────────

def _render_aol_gradebook(course_uuid, course_info, scheme, is_admin):
    st.subheader("📊 AOL Gradebook")

    # Generation controls
    with st.expander("🔄 Generate AOL Gradebook", expanded=True):
        st.caption("Select which components to include in this generation run.")
        c1, c2, c3, c4 = st.columns(4)
        inc_quiz = c1.checkbox("📝 Quizzes",     value=True, key="aol_inc_quiz")
        inc_asgn = c2.checkbox("📄 Assignments", value=True, key="aol_inc_asgn")
        inc_mid  = c3.checkbox("📘 Midterm",     value=True, key="aol_inc_mid")
        inc_fin  = c4.checkbox("📗 Final",       value=True, key="aol_inc_fin")

        components = []
        if inc_quiz: components.append("quiz")
        if inc_asgn: components.append("assignment")
        if inc_mid:  components.append("midterm")
        if inc_fin:  components.append("final")

        if st.button("🔄 Generate AOL Gradebook", type="primary",
                      use_container_width=True, key="aol_gen_btn"):
            if not components:
                st.error("Select at least one component.")
            else:
                with st.spinner("Generating..."):
                    ok, msg, count = UProService.generate_aol(course_uuid, components)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    st.divider()

    aol_rows = UProService.get_aol_gradebook(course_uuid)
    if not aol_rows:
        st.info("No AOL data generated yet.")
        return

    cfg = UProService.get_aol_config(course_uuid)

    section_header("Results", f"{len(aol_rows)} student(s)")

    # Summary table
    rows = []
    for g in aol_rows:
        p      = g.get("profiles", {}) or {}
        letter = g.get("letter_grade") or "—"
        total  = g.get("grand_total")
        syn    = (g.get("syndicates") or {}).get("name","—")
        suggs  = suggest_grade_change(total, scheme) if total is not None else []
        rows.append({
            "Name":         _pname(p),
            "Enrollment":   p.get("enrollment_number","—"),
            "Syndicate":    syn,
            "Quiz":         g.get("quiz_total","—"),
            "Assignment":   g.get("assignment_total","—"),
            "Midterm":      g.get("midterm_total","—"),
            "Final":        g.get("final_total","—"),
            "Total":        f"{total:.2f}" if total is not None else "—",
            "Grade":        f"{_grade_icon(letter)} {letter}",
            "GPA":          g.get("gpa_points","—"),
            "Suggestions":  " | ".join(suggs) if suggs else "—",
            "Status":       g.get("status","—").capitalize(),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Breakdown expanders
    with st.expander("🔍 Detailed Breakdown per Student"):
        sel_name = st.selectbox("Select Student", [r["Name"] for r in rows],
                                 key="aol_detail_sel")
        g = next((x for x in aol_rows if _pname(x.get("profiles",{})) == sel_name), None)
        if g:
            p = g.get("profiles", {}) or {}
            st.markdown(
                f"**{_pname(p)}** | Enroll: `{p.get('enrollment_number','')}` | "
                f"Syndicate: {(g.get('syndicates') or {}).get('name','—')}"
            )
            sub_c1, sub_c2, sub_c3, sub_c4 = st.columns(4)
            _show_breakdown(sub_c1, "Quiz",       g.get("quiz_breakdown",[]),       "quiz_no")
            _show_breakdown(sub_c2, "Assignment",  g.get("assignment_breakdown",[]), "assignment_no")
            _show_breakdown(sub_c3, "Midterm Q",  g.get("midterm_breakdown",[]),    "question_no")
            _show_breakdown(sub_c4, "Final Q",    g.get("final_breakdown",[]),      "question_no")

    # Grade distribution
    st.divider()
    section_header("Grade Distribution")
    grade_counts = {}
    for g in aol_rows:
        l = g.get("letter_grade") or "—"
        grade_counts[l] = grade_counts.get(l, 0) + 1
    st.bar_chart(pd.DataFrame(
        [{"Grade": k, "Count": v} for k, v in sorted(grade_counts.items())]
    ).set_index("Grade"))

    # Actions
    st.divider()
    statuses = {g["status"] for g in aol_rows}
    section_header("Workflow Actions")

    col1, col2, col3, col4 = st.columns(4)

    # Submit (faculty_ultra or admin)
    if "draft" in statuses:
        if col1.button("📤 Submit for Approval",
                        use_container_width=True, key="aol_submit"):
            if UProService.submit_aol(course_uuid):
                st.success("✅ Submitted.")
                st.rerun()

    # Approve & Release (admin only)
    if is_admin:
        if "submitted" in statuses:
            if col2.button("✅ Approve", use_container_width=True, key="aol_approve"):
                if UProService.approve_aol(course_uuid):
                    st.success("✅ Approved.")
                    st.rerun()
            if col3.button("📢 Approve & Release",
                            use_container_width=True, key="aol_apprel"):
                UProService.approve_aol(course_uuid)
                UProService.release_aol(course_uuid)
                st.success("✅ Approved and released.")
                st.rerun()
        if "approved" in statuses:
            if col4.button("📢 Release to Students",
                            use_container_width=True, key="aol_release"):
                if UProService.release_aol(course_uuid):
                    st.success("✅ Released.")
                    st.rerun()

    # Push to main gradebook
    st.divider()
    section_header("Push to Main Gradebook",
                    "Overwrites main compiled_grades with AOL totals")
    if st.button("⬆️ Push AOL Grades → Main Gradebook",
                  type="secondary", use_container_width=True, key="aol_push"):
        ok, msg = UProService.push_to_main_gradebook(course_uuid)
        if ok:
            st.success(f"✅ {msg}")
        else:
            st.error(f"❌ {msg}")

    # Excel export
    st.divider()
    excel_bytes = UProService.export_aol_to_excel(course_uuid, course_info)
    if excel_bytes:
        course_code = course_info.get("code","course").replace(" ","_")
        st.download_button(
            label="📥 Download AOL Gradebook (Excel)",
            data=excel_bytes,
            file_name=f"AOL_Gradebook_{course_code}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def _show_breakdown(col, label, breakdown, key_field):
    if not breakdown:
        col.caption(f"{label}: —")
        return
    col.markdown(f"**{label}**")
    for item in breakdown:
        no  = item.get(key_field, "?")
        obt = item.get("obtained","—")
        mx  = item.get("max_marks","—")
        col.caption(f"#{no}: {obt}/{mx}")


# ── AOL CONFIG ────────────────────────────────────────────────────

def _render_aol_config(course_uuid):
    st.subheader("⚙️ AOL Generation Configuration")
    st.caption("Defines how marks are distributed when generating the AOL Gradebook.")

    cfg = UProService.get_aol_config(course_uuid)

    with st.form("aol_cfg_form"):
        section_header("Quizzes")
        c1, c2 = st.columns(2)
        num_q      = c1.number_input("Number of quizzes",      min_value=1, value=int(cfg["num_quizzes"]))
        q_max      = c2.number_input("Max marks per quiz",      min_value=1.0, value=float(cfg["quiz_max_marks"]), step=0.5)

        section_header("Assignments")
        c3, c4 = st.columns(2)
        num_a  = c3.number_input("Number of assignments",   min_value=1, value=int(cfg["num_assignments"]))
        a_max  = c4.number_input("Max marks per assignment", min_value=1.0, value=float(cfg["assignment_max_marks"]), step=0.5)

        section_header("Midterm Questions")
        num_mq = st.number_input("Number of midterm questions", min_value=1, value=int(cfg["num_midterm_questions"]))
        mid_marks_str = st.text_input(
            "Max marks per question (comma-separated)",
            value=", ".join(str(x) for x in cfg["midterm_q_marks"]),
            help="e.g. 12.5, 12.5"
        )

        section_header("Final Questions")
        num_fq = st.number_input("Number of final questions", min_value=1, value=int(cfg["num_final_questions"]))
        fin_marks_str = st.text_input(
            "Max marks per question (comma-separated)",
            value=", ".join(str(x) for x in cfg["final_q_marks"]),
            help="e.g. 15, 15, 10"
        )

        submitted = st.form_submit_button("💾 Save Config", use_container_width=True)

    if submitted:
        try:
            mid_marks = [float(x.strip()) for x in mid_marks_str.split(",") if x.strip()]
            fin_marks = [float(x.strip()) for x in fin_marks_str.split(",") if x.strip()]
        except ValueError:
            st.error("Invalid marks format. Use comma-separated numbers.")
            return

        ok = UProService.save_aol_config(course_uuid, {
            "num_quizzes":           int(num_q),
            "quiz_max_marks":        float(q_max),
            "num_assignments":       int(num_a),
            "assignment_max_marks":  float(a_max),
            "num_midterm_questions": int(num_mq),
            "midterm_q_marks":       mid_marks,
            "num_final_questions":   int(num_fq),
            "final_q_marks":         fin_marks,
        })
        if ok:
            st.success("✅ AOL config saved.")
            st.rerun()
        else:
            st.error("❌ Save failed.")
