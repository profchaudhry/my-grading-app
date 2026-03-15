# _UPRO_VERSION = 2
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
    import datetime as _dt
    import math

    st.subheader("👥 Syndicate Management")

    all_syndicates  = UProService.get_syndicates(course_uuid)
    confirmed       = [s for s in all_syndicates if s.get("status") == "confirmed"]
    enrolled_count  = len(enrolled_profiles)
    syn_cfg         = UProService.get_syndicate_config(course_uuid)
    max_members     = syn_cfg["max_syndicate_members"]
    join_open       = UProService.is_join_open(course_uuid)
    deadline_str    = syn_cfg.get("syndicate_join_deadline")
    max_syndicates  = UProService.get_allowed_syndicate_count(course_uuid, enrolled_count)

    # ── Settings panel ────────────────────────────────────────
    with st.expander("⚙️ Syndicate Settings", expanded=False):
        section_header("Limits & Deadline")
        sc1, sc2 = st.columns(2)
        new_max = sc1.number_input(
            "Max members per syndicate", min_value=1, max_value=50,
            value=max_members, step=1, key="syn_max_members"
        )
        # Deadline
        deadline_val = None
        if deadline_str:
            try:
                deadline_val = _dt.date.fromisoformat(str(deadline_str))
            except Exception:
                deadline_val = None
        if "syn_dl_key" not in st.session_state:
            st.session_state["syn_dl_key"] = deadline_val or _dt.date.today()
        new_dl = sc2.date_input("Join deadline (students can't join/leave after this)",
                                 value=st.session_state["syn_dl_key"], key="syn_deadline")
        clear_dl = sc2.checkbox("No deadline (always open)", value=(deadline_str is None),
                                 key="syn_no_dl")

        st.caption(
            f"📊 {enrolled_count} enrolled → max **{max_syndicates}** syndicates "
            f"of {new_max} each"
        )
        if st.button("💾 Save Syndicate Settings", key="syn_cfg_save",
                     use_container_width=True, type="primary"):
            dl_to_save = None if clear_dl else str(new_dl)
            ok = UProService.save_syndicate_config(course_uuid, int(new_max), dl_to_save)
            if ok:
                st.success("✅ Settings saved.")
                st.rerun()
            else:
                st.error("❌ Save failed.")

    st.divider()

    # ── Status bar ────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Enrolled Students", enrolled_count)
    m2.metric("Allowed Syndicates", max_syndicates)
    m3.metric("Created Syndicates", len(confirmed))
    m4.metric("Join Period", "Open ✅" if join_open else "Closed 🔒")

    st.divider()

    # ── Create syndicate ──────────────────────────────────────
    with st.expander("➕ Create New Syndicate", expanded=False):
        if len(confirmed) >= max_syndicates:
            st.warning(
                f"Maximum syndicates ({max_syndicates}) reached for {enrolled_count} students."
            )
        else:
            cn1, cn2 = st.columns(2)
            new_syn_name = cn1.text_input("Syndicate Name", placeholder="e.g. Alpha Team",
                                           key="admin_syn_name")
            lead_options = ["— No lead yet —"] + list(student_map.keys())
            lead_sel     = cn2.selectbox("Initial Lead (optional)", lead_options,
                                          key="admin_syn_lead")
            if st.button("➕ Create", key="admin_create_syn",
                         use_container_width=True, type="primary"):
                name = new_syn_name.strip()
                if not name:
                    st.error("Name is required.")
                elif any(s["name"].lower() == name.lower() for s in confirmed):
                    st.error("A syndicate with this name already exists.")
                else:
                    lead_id = student_map[lead_sel]["id"] if lead_sel != "— No lead yet —" else None
                    result  = UProService.create_syndicate(
                        course_uuid, name, lead_id,
                        created_by_role="admin" if is_admin else "faculty_ultra",
                        status="confirmed"
                    )
                    if result:
                        st.success(f"✅ Syndicate '{name}' created.")
                        st.rerun()
                    else:
                        st.error("❌ Failed.")

    st.divider()

    # ── Confirmed syndicates ──────────────────────────────────
    assigned_ids: set = set()
    for syn in confirmed:
        for m in UProService.get_syndicate_members(syn["id"]):
            assigned_ids.add(m["student_id"])

    section_header("Confirmed Syndicates", f"{len(confirmed)} / {max_syndicates} slots used")

    if not confirmed:
        st.info("No syndicates yet.")
    else:
        for syn in confirmed:
            members  = UProService.get_syndicate_members(syn["id"])
            lead_id  = syn.get("lead_student_id")
            lead_p   = syn.get("profiles") or {}
            lead_nm  = _pname(lead_p) if lead_p else "—"
            spots    = max_members - len(members)

            with st.expander(
                f"🏷️ **{syn['name']}** | Lead: {lead_nm} | "
                f"{len(members)}/{max_members} members | "
                f"{'✅ Open' if spots > 0 else '🔒 Full'}"
            ):
                # Member list with remove
                for m in members:
                    mp      = m.get("profiles", {}) or {}
                    is_lead = mp.get("id") == lead_id
                    mc1, mc2 = st.columns([7, 1])
                    mc1.markdown(
                        f"{'👑 ' if is_lead else '👤 '}"
                        f"**{_pname(mp)}** `{mp.get('enrollment_number','')}`"
                        + (" *(Lead)*" if is_lead else "")
                    )
                    if mc2.button("✖", key=f"rm_{syn['id']}_{mp.get('id')}",
                                   help="Remove from syndicate"):
                        UProService.remove_member(syn["id"], mp["id"])
                        st.rerun()

                st.divider()

                # ── Add member ────────────────────────────────
                if spots > 0:
                    available = [p for p in enrolled_profiles
                                 if p["id"] not in {m["student_id"] for m in members}]
                    if available:
                        add_opts = [_pname(p) for p in available]
                        add_sel  = st.selectbox("Add student", add_opts,
                                                key=f"add_sel_{syn['id']}")
                        if st.button("➕ Add", key=f"add_btn_{syn['id']}",
                                     use_container_width=True):
                            target = next(p for p in available if _pname(p) == add_sel)
                            if UProService.add_member(syn["id"], course_uuid, target["id"]):
                                st.success(f"✅ {add_sel} added.")
                                st.rerun()
                            else:
                                st.error("Failed.")

                # ── Rename syndicate ──────────────────────────
                with st.expander("✏️ Rename syndicate", expanded=False):
                    new_name = st.text_input("New name", value=syn["name"],
                                              key=f"rename_{syn['id']}")
                    if st.button("💾 Save name", key=f"rename_btn_{syn['id']}"):
                        if new_name.strip():
                            UProService.update_syndicate(syn["id"], {"name": new_name.strip()})
                            st.success("Renamed.")
                            st.rerun()

                # ── Appoint/change lead ───────────────────────
                if members:
                    member_profiles = [m.get("profiles", {}) for m in members]
                    lead_opts = [_pname(p) for p in member_profiles]
                    cur_idx   = next(
                        (i for i, p in enumerate(member_profiles)
                         if p.get("id") == lead_id), 0
                    )
                    new_lead_sel = st.selectbox("Appoint Lead", lead_opts,
                                                index=cur_idx, key=f"lead_{syn['id']}")
                    if st.button("👑 Set Lead", key=f"lead_btn_{syn['id']}",
                                  use_container_width=True):
                        new_lead = next(p for p in member_profiles
                                        if _pname(p) == new_lead_sel)
                        UProService.update_syndicate(syn["id"],
                                                      {"lead_student_id": new_lead["id"]})
                        st.success(f"👑 {new_lead_sel} appointed as lead.")
                        st.rerun()

                # ── Vote tally (after deadline) ───────────────
                if not join_open:
                    votes = UProService.get_votes(syn["id"])
                    if votes:
                        with st.expander(f"🗳️ Vote tally ({len(votes)} votes)"):
                            tally: dict = {}
                            for v in votes:
                                nm = v.get("nominee") or {}
                                nname = _pname(nm) if nm else v.get("nominee_id","?")
                                tally[nname] = tally.get(nname, 0) + 1
                            for nm, cnt in sorted(tally.items(),
                                                   key=lambda x: -x[1]):
                                st.caption(f"{nm}: {cnt} vote(s)")

                # ── Delete syndicate ──────────────────────────
                st.divider()
                if st.button("🗑️ Delete Syndicate", key=f"del_{syn['id']}",
                              type="secondary"):
                    UProService.delete_syndicate(syn["id"])
                    st.rerun()

    # ── Unassigned students ───────────────────────────────────
    unassigned = [p for p in enrolled_profiles if p["id"] not in assigned_ids]
    if unassigned:
        st.divider()
        section_header("⚠️ Unassigned Students",
                        f"{len(unassigned)} not in any syndicate")
        for p in unassigned:
            uc1, uc2 = st.columns([5, 3])
            uc1.caption(f"• **{_pname(p)}** `{p.get('enrollment_number','')}`")
            if confirmed:
                has_spots = [s for s in confirmed
                             if len(UProService.get_syndicate_members(s["id"])) < max_members]
                if has_spots:
                    dest_opts = [s["name"] for s in has_spots]
                    dest_sel  = uc2.selectbox("Assign to", dest_opts,
                                               key=f"unassign_dest_{p['id']}")
                    dest_syn  = next(s for s in has_spots if s["name"] == dest_sel)
                    if st.button(f"➕ Assign {_pname(p)}",
                                  key=f"assign_btn_{p['id']}"):
                        UProService.add_member(dest_syn["id"], course_uuid, p["id"])
                        st.success(f"Assigned to {dest_sel}.")
                        st.rerun()


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
            # Seed group input default on first render only
            if "upro_asgn_group" not in st.session_state:
                st.session_state["upro_asgn_group"] = 0.0
            group_val = st.number_input(
                f"Group Assignment Score (out of {max_asgn})",
                min_value=0.0, max_value=max_asgn,
                step=0.5, key="upro_asgn_group"
            )
            if st.button("Apply to all members ↓", key="upro_asgn_apply"):
                # Write directly into each member widget's session_state key
                # so Streamlit uses the new value on the next render
                for _m in members:
                    _mp = _m.get("profiles", {}) or {}
                    _sid = _mp.get("id")
                    if _sid:
                        st.session_state[f"upro_asgn_{_sid}"] = min(float(group_val), max_asgn)
                st.rerun()

            st.divider()
            # Individual inputs — keyed per student; session_state values set above on Apply
            entries = {}
            for m in members:
                mp  = m.get("profiles", {}) or {}
                sid = mp["id"]
                existing = UProService.get_student_upro_score(course_uuid, sid)
                widget_key = f"upro_asgn_{sid}"
                # Only set default if the key isn't already in session_state
                # (preserves Apply value OR previously-typed value)
                if widget_key not in st.session_state:
                    if existing and existing.get("assignment_score") is not None:
                        st.session_state[widget_key] = float(existing["assignment_score"])
                    else:
                        st.session_state[widget_key] = 0.0
                is_lead = sid == sel_syn.get("lead_student_id")
                entries[sid] = st.number_input(
                    f"{'👑 ' if is_lead else ''}{_pname(mp)} "
                    f"`{mp.get('enrollment_number','')}`",
                    min_value=0.0, max_value=max_asgn,
                    step=0.5,
                    key=widget_key
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

    # ── Build dynamic column headers based on config ───────────
    nq  = int(cfg.get("num_quizzes", 0))
    na  = int(cfg.get("num_assignments", 0))
    q_maxs = cfg.get("quiz_marks_list", [])
    a_maxs = cfg.get("assignment_marks_list", [])
    mq_maxs = cfg.get("midterm_q_marks", [])
    fq_maxs = cfg.get("final_q_marks", [])

    rows = []
    for g in aol_rows:
        p      = g.get("profiles", {}) or {}
        letter = g.get("letter_grade") or "—"
        total  = g.get("grand_total")
        syn    = (g.get("syndicates") or {}).get("name", "—")
        suggs  = suggest_grade_change(total, scheme) if total is not None else []

        # Parse breakdowns
        qb  = _parse_breakdown(g.get("quiz_breakdown"))
        ab  = _parse_breakdown(g.get("assignment_breakdown"))
        mb  = _parse_breakdown(g.get("midterm_breakdown"))
        fb  = _parse_breakdown(g.get("final_breakdown"))

        row = {
            "Name":       _pname(p),
            "Enrollment": p.get("enrollment_number", "—"),
            "Syndicate":  syn,
        }

        # Individual quiz scores
        for i in range(nq):
            mx  = q_maxs[i] if i < len(q_maxs) else "?"
            obt = qb[i]["obtained"] if i < len(qb) else "—"
            row[f"Q{i+1} (/{mx})"] = obt

        # Quiz total and original UPro input score
        q_tot      = g.get("quiz_total")
        q_max_sum  = sum(q_maxs) if q_maxs else "?"
        q_meta     = _extract_upro_meta(g.get("quiz_breakdown"))
        quiz_upro  = q_meta.get("upro_score")
        q_weight   = q_meta.get("weight") or scheme.get("weight_quiz", "?")
        row[f"Quiz Total (/{q_max_sum})"] = f"{q_tot:.2f}" if q_tot is not None else "—"
        row[f"Quiz UPro Score (/{q_weight})"] = (
            f"{quiz_upro:.2f}" if quiz_upro is not None else "—"
        )

        # Individual assignment scores
        for i in range(na):
            mx  = a_maxs[i] if i < len(a_maxs) else "?"
            obt = ab[i]["obtained"] if i < len(ab) else "—"
            row[f"A{i+1} (/{mx})"] = obt

        a_tot      = g.get("assignment_total")
        a_max_sum  = sum(a_maxs) if a_maxs else "?"
        a_meta     = _extract_upro_meta(g.get("assignment_breakdown"))
        asgn_upro  = a_meta.get("upro_score")
        a_weight   = a_meta.get("weight") or scheme.get("weight_assignment", "?")
        row[f"Asgn Total (/{a_max_sum})"] = f"{a_tot:.2f}" if a_tot is not None else "—"
        row[f"Asgn UPro Score (/{a_weight})"] = (
            f"{asgn_upro:.2f}" if asgn_upro is not None else "—"
        )

        # Midterm questions
        for i, item in enumerate(mb):
            mx  = item.get("max_marks", mq_maxs[i] if i < len(mq_maxs) else "?")
            row[f"MQ{i+1} (/{mx})"] = item.get("obtained", "—")
        m_tot = g.get("midterm_total")
        mq_sum = sum(mq_maxs) if mq_maxs else "?"
        row[f"Midterm (/{mq_sum})"] = f"{m_tot:.2f}" if m_tot is not None else "—"

        # Final questions
        for i, item in enumerate(fb):
            mx  = item.get("max_marks", fq_maxs[i] if i < len(fq_maxs) else "?")
            row[f"FQ{i+1} (/{mx})"] = item.get("obtained", "—")
        f_tot = g.get("final_total")
        fq_sum = sum(fq_maxs) if fq_maxs else "?"
        row[f"Final (/{fq_sum})"] = f"{f_tot:.2f}" if f_tot is not None else "—"

        row["▶ Total"]       = f"{total:.2f}" if total is not None else "—"
        row["Grade"]         = f"{_grade_icon(letter)} {letter}"
        row["GPA"]           = g.get("gpa_points", "—")
        row["Suggestions"]   = " | ".join(suggs) if suggs else "—"
        row["Status"]        = g.get("status", "—").capitalize()
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Per-student detailed breakdown expander ────────────────
    with st.expander("🔍 Detailed Breakdown per Student"):
        sel_name = st.selectbox("Select Student", [r["Name"] for r in rows],
                                 key="aol_detail_sel")
        g = next((x for x in aol_rows if _pname(x.get("profiles", {})) == sel_name), None)
        if g:
            p   = g.get("profiles", {}) or {}
            syn = (g.get("syndicates") or {}).get("name", "—")
            st.markdown(
                f"**{_pname(p)}** | Enroll: `{p.get('enrollment_number','')}` | "
                f"Syndicate: {syn}"
            )
            qb = _parse_breakdown(g.get("quiz_breakdown"))
            ab = _parse_breakdown(g.get("assignment_breakdown"))
            mb = _parse_breakdown(g.get("midterm_breakdown"))
            fb = _parse_breakdown(g.get("final_breakdown"))

            bc1, bc2 = st.columns(2)
            with bc1:
                if qb:
                    st.markdown("**📝 Quizzes**")
                    for item in qb:
                        st.caption(f"Quiz {item.get('quiz_no','?')}: "
                                   f"**{item.get('obtained','—')}** / {item.get('max_marks','?')}")
                    q_tot     = g.get("quiz_total")
                    q_max_sum = sum(q_maxs) if q_maxs else "?"
                    st.markdown(f"**Quiz Total: {q_tot if q_tot is not None else '—'} / {q_max_sum}**")
                    q_meta2   = _extract_upro_meta(g.get("quiz_breakdown"))
                    quiz_upro = q_meta2.get("upro_score")
                    w_q       = q_meta2.get("weight") or scheme.get("weight_quiz", "?")
                    st.markdown(f"**Quiz UPro Score (entered): {f'{quiz_upro:.2f}' if quiz_upro is not None else '—'} / {w_q}**")
            with bc2:
                if ab:
                    st.markdown("**📄 Assignments**")
                    for item in ab:
                        st.caption(f"Asgn {item.get('assignment_no','?')}: "
                                   f"**{item.get('obtained','—')}** / {item.get('max_marks','?')}")
                    a_tot     = g.get("assignment_total")
                    a_max_sum = sum(a_maxs) if a_maxs else "?"
                    st.markdown(f"**Asgn Total: {a_tot if a_tot is not None else '—'} / {a_max_sum}**")
                    a_meta2   = _extract_upro_meta(g.get("assignment_breakdown"))
                    asgn_upro = a_meta2.get("upro_score")
                    w_a       = a_meta2.get("weight") or scheme.get("weight_assignment", "?")
                    st.markdown(f"**Asgn UPro Score (entered): {f'{asgn_upro:.2f}' if asgn_upro is not None else '—'} / {w_a}**")

            bc3, bc4 = st.columns(2)
            with bc3:
                if mb:
                    st.markdown("**📘 Midterm Questions**")
                    for item in mb:
                        st.caption(f"Q{item.get('question_no','?')}: "
                                   f"**{item.get('obtained','—')}** / {item.get('max_marks','?')}")
                    m_tot = g.get("midterm_total")
                    st.markdown(f"**Midterm Total: {m_tot if m_tot is not None else '—'} / {sum(mq_maxs) if mq_maxs else '?'}**")
            with bc4:
                if fb:
                    st.markdown("**📗 Final Questions**")
                    for item in fb:
                        st.caption(f"Q{item.get('question_no','?')}: "
                                   f"**{item.get('obtained','—')}** / {item.get('max_marks','?')}")
                    f_tot = g.get("final_total")
                    st.markdown(f"**Final Total: {f_tot if f_tot is not None else '—'} / {sum(fq_maxs) if fq_maxs else '?'}**")

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


def _parse_breakdown(raw) -> list:
    """Safely parse a breakdown field. Returns only the real items (no _meta)."""
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    if isinstance(raw, list):
        return [item for item in raw if "_upro_score" not in item]
    return []


def _extract_upro_meta(raw) -> dict:
    """Extract the embedded UPro score metadata from a breakdown field.
    Returns {"upro_score": float, "weight": float} or {}."""
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return {}
    if isinstance(raw, list):
        for item in raw:
            if "_upro_score" in item:
                return {"upro_score": item["_upro_score"], "weight": item.get("_weight")}
    return {}


def _show_breakdown(col, label, breakdown, key_field):
    """Legacy helper kept for compatibility."""
    items = _parse_breakdown(breakdown)
    if not items:
        col.caption(f"{label}: —")
        return
    col.markdown(f"**{label}**")
    for item in items:
        no  = item.get(key_field, "?")
        obt = item.get("obtained", "—")
        mx  = item.get("max_marks", "—")
        col.caption(f"#{no}: {obt}/{mx}")


# ── AOL CONFIG ────────────────────────────────────────────────────

def _render_aol_config(course_uuid):
    st.subheader("⚙️ AOL Generation Configuration")
    st.caption("Define the number of quizzes/assignments and max marks for each item individually.")

    cfg = UProService.get_aol_config(course_uuid)

    # ── QUIZZES ────────────────────────────────────────────────
    section_header("Quizzes")
    num_q = st.number_input("Number of quizzes", min_value=1, max_value=20,
                             value=int(cfg["num_quizzes"]), step=1, key="cfg_num_q")

    # Same-for-all convenience
    qc1, qc2 = st.columns([3, 1])
    q_same = qc1.number_input("Set same max marks for ALL quizzes",
                               min_value=0.5, value=10.0, step=0.5, key="cfg_q_same")
    if qc2.button("Apply to all ↓", key="cfg_q_apply"):
        for i in range(int(num_q)):
            st.session_state[f"cfg_q_{i}"] = float(q_same)
        st.rerun()

    # Individual quiz marks
    quiz_marks = []
    q_cols = st.columns(min(int(num_q), 5))
    existing_q = cfg.get("quiz_marks_list", [10.0] * int(num_q))
    for i in range(int(num_q)):
        col = q_cols[i % len(q_cols)]
        key = f"cfg_q_{i}"
        if key not in st.session_state:
            st.session_state[key] = float(existing_q[i]) if i < len(existing_q) else 10.0
        val = col.number_input(f"Q{i+1} max", min_value=0.5, step=0.5, key=key)
        quiz_marks.append(val)

    st.divider()

    # ── ASSIGNMENTS ────────────────────────────────────────────
    section_header("Assignments")
    num_a = st.number_input("Number of assignments", min_value=1, max_value=20,
                             value=int(cfg["num_assignments"]), step=1, key="cfg_num_a")

    ac1, ac2 = st.columns([3, 1])
    a_same = ac1.number_input("Set same max marks for ALL assignments",
                               min_value=0.5, value=10.0, step=0.5, key="cfg_a_same")
    if ac2.button("Apply to all ↓", key="cfg_a_apply"):
        for i in range(int(num_a)):
            st.session_state[f"cfg_a_{i}"] = float(a_same)
        st.rerun()

    asgn_marks = []
    a_cols = st.columns(min(int(num_a), 5))
    existing_a = cfg.get("assignment_marks_list", [10.0] * int(num_a))
    for i in range(int(num_a)):
        col = a_cols[i % len(a_cols)]
        key = f"cfg_a_{i}"
        if key not in st.session_state:
            st.session_state[key] = float(existing_a[i]) if i < len(existing_a) else 10.0
        val = col.number_input(f"A{i+1} max", min_value=0.5, step=0.5, key=key)
        asgn_marks.append(val)

    st.divider()

    # ── MIDTERM QUESTIONS ──────────────────────────────────────
    section_header("Midterm Questions")
    num_mq = st.number_input("Number of midterm questions", min_value=1, max_value=20,
                              value=int(cfg["num_midterm_questions"]), step=1, key="cfg_num_mq")
    mid_marks = []
    mq_cols = st.columns(min(int(num_mq), 5))
    existing_mq = cfg.get("midterm_q_marks", [12.5] * int(num_mq))
    for i in range(int(num_mq)):
        col = mq_cols[i % len(mq_cols)]
        key = f"cfg_mq_{i}"
        if key not in st.session_state:
            st.session_state[key] = float(existing_mq[i]) if i < len(existing_mq) else 12.5
        val = col.number_input(f"MQ{i+1} max", min_value=0.5, step=0.5, key=key)
        mid_marks.append(val)

    st.divider()

    # ── FINAL QUESTIONS ────────────────────────────────────────
    section_header("Final Questions")
    num_fq = st.number_input("Number of final questions", min_value=1, max_value=20,
                              value=int(cfg["num_final_questions"]), step=1, key="cfg_num_fq")
    fin_marks = []
    fq_cols = st.columns(min(int(num_fq), 5))
    existing_fq = cfg.get("final_q_marks", [15.0] * int(num_fq))
    for i in range(int(num_fq)):
        col = fq_cols[i % len(fq_cols)]
        key = f"cfg_fq_{i}"
        if key not in st.session_state:
            st.session_state[key] = float(existing_fq[i]) if i < len(existing_fq) else 15.0
        val = col.number_input(f"FQ{i+1} max", min_value=0.5, step=0.5, key=key)
        fin_marks.append(val)

    st.divider()

    # ── Validation summary ─────────────────────────────────────
    q_total  = sum(quiz_marks)
    a_total  = sum(asgn_marks)
    mq_total = sum(mid_marks)
    fq_total = sum(fin_marks)
    st.caption(
        f"📊 Totals — Quizzes: **{q_total}** | Assignments: **{a_total}** | "
        f"Midterm Qs: **{mq_total}** | Final Qs: **{fq_total}**"
    )

    if st.button("💾 Save AOL Config", type="primary", use_container_width=True, key="cfg_save"):
        ok = UProService.save_aol_config(course_uuid, {
            "num_quizzes":           int(num_q),
            "quiz_marks_list":       quiz_marks,
            "num_assignments":       int(num_a),
            "assignment_marks_list": asgn_marks,
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
