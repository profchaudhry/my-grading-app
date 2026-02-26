"""
Gradebook UI — used by both faculty_console and admin_console.
Handles: scheme editor, quiz/assignment/exam setup,
marks entry (individual + bulk table), compile, submit/approve/release.
"""
import streamlit as st
import pandas as pd
from services.grading_service import GradingService, score_to_letter, suggest_grade_change
from services.enrollment_service import EnrollmentService
from ui.styles import section_header


# ── Helpers ───────────────────────────────────────────────────────

def _student_display_name(profile: dict) -> str:
    full = (profile.get("full_name") or "").strip()
    if full:
        return full
    first = (profile.get("first_name") or "").strip()
    last  = (profile.get("last_name")  or "").strip()
    return f"{first} {last}".strip() or profile.get("enrollment_number", "—")


def _grade_colour(letter: str) -> str:
    if not letter:
        return ""
    if letter.startswith("A"):
        return "🟢"
    if letter.startswith("B"):
        return "🔵"
    if letter.startswith("C"):
        return "🟡"
    if letter.startswith("D"):
        return "🟠"
    return "🔴"


# ── Scheme editor ─────────────────────────────────────────────────

def render_scheme_editor(course_uuid: str, is_admin: bool = False) -> None:
    scheme   = GradingService.get_effective_scheme(course_uuid)
    global_s = GradingService.get_global_scheme()
    is_overridden = scheme.get("course_id") is not None

    st.markdown(
        f"**Using:** {'📌 Course override' if is_overridden else '🌐 Global scheme'}"
    )
    if is_overridden and st.button("↩️ Reset to Global Scheme", key="reset_scheme"):
        if GradingService.reset_course_scheme(course_uuid):
            st.success("✅ Reset to global scheme.")
            st.rerun()

    with st.expander(
        "⚙️ Edit Grading Scheme" + (" (Admin: also edits global)" if is_admin else ""),
        expanded=False
    ):
        with st.form("scheme_form"):
            section_header("Component Weights", "Must sum to 100")
            c1, c2, c3, c4 = st.columns(4)
            w_quiz = c1.number_input("Quiz %",       min_value=0.0, max_value=100.0,
                                      value=float(scheme["weight_quiz"]),       step=1.0)
            w_asgn = c2.number_input("Assignment %", min_value=0.0, max_value=100.0,
                                      value=float(scheme["weight_assignment"]),  step=1.0)
            w_mid  = c3.number_input("Midterm %",    min_value=0.0, max_value=100.0,
                                      value=float(scheme["weight_midterm"]),     step=1.0)
            w_fin  = c4.number_input("Final %",      min_value=0.0, max_value=100.0,
                                      value=float(scheme["weight_final"]),       step=1.0)

            st.divider()
            section_header("Letter Grade Thresholds", "Lower bound of each grade")
            r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
            g_a    = r1c1.number_input("A ≥",   value=float(scheme["grade_a_min"]),   step=1.0)
            g_am   = r1c2.number_input("A- ≥",  value=float(scheme["grade_a_m_min"]), step=1.0)
            g_bp   = r1c3.number_input("B+ ≥",  value=float(scheme["grade_bp_min"]),  step=1.0)
            g_b    = r1c4.number_input("B ≥",   value=float(scheme["grade_b_min"]),   step=1.0)
            g_bm   = r1c5.number_input("B- ≥",  value=float(scheme["grade_b_m_min"]), step=1.0)
            r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
            g_cp   = r2c1.number_input("C+ ≥",  value=float(scheme["grade_cp_min"]),  step=1.0)
            g_c    = r2c2.number_input("C ≥",   value=float(scheme["grade_c_min"]),   step=1.0)
            g_cm   = r2c3.number_input("C- ≥",  value=float(scheme["grade_c_m_min"]), step=1.0)
            g_dp   = r2c4.number_input("D+ ≥",  value=float(scheme["grade_dp_min"]),  step=1.0)
            g_d    = r2c5.number_input("D ≥",   value=float(scheme["grade_d_min"]),   step=1.0)
            st.caption("F = anything below D threshold")

            save_global = st.checkbox("Also update the Global Scheme",
                                       value=False, disabled=not is_admin) if is_admin else False
            submitted = st.form_submit_button("💾 Save Scheme", use_container_width=True)

        if submitted:
            total_w = w_quiz + w_asgn + w_mid + w_fin
            if round(total_w) != 100:
                st.error(f"Weights must sum to 100. Current sum: {total_w}")
            else:
                data = {
                    "weight_quiz": w_quiz, "weight_assignment": w_asgn,
                    "weight_midterm": w_mid, "weight_final": w_fin,
                    "grade_a_min": g_a, "grade_a_m_min": g_am,
                    "grade_bp_min": g_bp, "grade_b_min": g_b, "grade_b_m_min": g_bm,
                    "grade_cp_min": g_cp, "grade_c_min": g_c, "grade_c_m_min": g_cm,
                    "grade_dp_min": g_dp, "grade_d_min": g_d,
                }
                ok = GradingService.save_course_scheme(course_uuid, data.copy())
                if is_admin and save_global:
                    GradingService.update_global_scheme(data.copy())
                if ok:
                    st.success("✅ Scheme saved.")
                    st.rerun()
                else:
                    st.error("❌ Save failed.")


# ── Quiz manager ──────────────────────────────────────────────────

def render_quiz_manager(course_uuid: str, students: list) -> None:
    quizzes  = GradingService.get_quizzes(course_uuid)
    quiz_cfg = GradingService.get_quiz_config(course_uuid)
    scheme   = GradingService.get_effective_scheme(course_uuid)

    tab_setup, tab_marks = st.tabs(["⚙️ Setup Quizzes", "✏️ Enter Marks"])

    # ── Setup ──────────────────────────────────────────────────────
    with tab_setup:
        section_header("Scoring Method")
        with st.form("quiz_cfg_form"):
            method = st.radio(
                "Quiz scoring method",
                ["equal", "weighted", "best_of"],
                index=["equal","weighted","best_of"].index(quiz_cfg.get("method","equal")),
                format_func=lambda x: {
                    "equal":    "Equal weight (sum all)",
                    "weighted": "Custom weights per quiz",
                    "best_of":  "Best of N quizzes",
                }[x],
                horizontal=True,
            )
            best_of_n = None
            if method == "best_of":
                best_of_n = st.number_input("Best of N", min_value=1,
                                             max_value=max(len(quizzes),1), value=
                                             int(quiz_cfg.get("best_of_n") or 1), step=1)
            if st.form_submit_button("Save Method", use_container_width=True):
                GradingService.save_quiz_config(course_uuid, method, best_of_n)
                st.success("✅ Saved.")
                st.rerun()

        st.divider()
        section_header("Quizzes", f"{len(quizzes)} defined")

        with st.form("add_quiz_form"):
            c1, c2, c3, c4, c5 = st.columns([3,1,1,2,1])
            q_title  = c1.text_input("Title",       placeholder="Quiz 1")
            q_total  = c2.number_input("Out of",    min_value=1.0, value=10.0, step=1.0)
            q_weight = c3.number_input("Weight",    min_value=0.0, value=0.0,  step=0.5,
                                        help="0 = equal weight")
            q_clo    = c4.text_input("CLO (optional)", placeholder="CLO-1")
            q_order  = c5.number_input("Order", min_value=1, value=len(quizzes)+1, step=1)
            if st.form_submit_button("➕ Add Quiz", use_container_width=True):
                if not q_title:
                    st.error("Title required.")
                else:
                    ok = GradingService.add_quiz(
                        course_uuid, q_title, q_total,
                        q_weight if q_weight > 0 else None,
                        q_clo, q_order
                    )
                    if ok:
                        st.success(f"✅ '{q_title}' added.")
                        st.rerun()

        if quizzes:
            for q in quizzes:
                with st.expander(f"📝 {q['title']} — out of {q['total_marks']}"):
                    with st.form(f"edit_quiz_{q['id']}"):
                        c1, c2, c3, c4 = st.columns([3,1,1,2])
                        new_title  = c1.text_input("Title",  value=q["title"])
                        new_total  = c2.number_input("Out of", value=float(q["total_marks"]), step=1.0)
                        new_weight = c3.number_input("Weight", value=float(q["weight"] or 0), step=0.5)
                        new_clo    = c4.text_input("CLO",    value=q.get("clo_no",""))
                        s1, s2 = st.columns(2)
                        if s1.form_submit_button("💾 Save"):
                            GradingService.update_quiz(q["id"], {
                                "title": new_title, "total_marks": new_total,
                                "weight": new_weight if new_weight > 0 else None,
                                "clo_no": new_clo,
                            })
                            st.success("✅ Updated.")
                            st.rerun()
                        if s2.form_submit_button("🗑️ Delete", type="secondary"):
                            GradingService.delete_quiz(q["id"])
                            st.warning("Deleted.")
                            st.rerun()

    # ── Marks entry ────────────────────────────────────────────────
    with tab_marks:
        if not quizzes:
            st.info("Add quizzes in the Setup tab first.")
            return
        if not students:
            st.info("No students enrolled in this course.")
            return

        sel_quiz_label = st.selectbox(
            "Select Quiz",
            [f"{q['title']} (/{q['total_marks']})" for q in quizzes],
            key="sel_quiz"
        )
        sel_quiz = quizzes[[f"{q['title']} (/{q['total_marks']})"
                             for q in quizzes].index(sel_quiz_label)]

        entry_mode = st.radio("Entry mode", ["📋 Table (bulk)", "👤 Individual"],
                               horizontal=True, key="quiz_entry_mode")

        existing_marks = {
            m["student_id"]: m["obtained"]
            for m in GradingService.get_quiz_marks(sel_quiz["id"])
        }

        if entry_mode == "📋 Table (bulk)":
            _render_bulk_marks_table(
                students, existing_marks,
                float(sel_quiz["total_marks"]),
                save_fn=lambda sid, val: GradingService.save_quiz_mark(
                    sel_quiz["id"], sid, val),
                key_prefix=f"quiz_{sel_quiz['id']}"
            )
        else:
            _render_individual_marks(
                students, existing_marks,
                float(sel_quiz["total_marks"]),
                save_fn=lambda sid, val: GradingService.save_quiz_mark(
                    sel_quiz["id"], sid, val),
                key_prefix=f"quiz_ind_{sel_quiz['id']}"
            )


# ── Assignment manager ────────────────────────────────────────────

def render_assignment_manager(course_uuid: str, students: list) -> None:
    asgns    = GradingService.get_assignments(course_uuid)
    asgn_cfg = GradingService.get_assignment_config(course_uuid)

    tab_setup, tab_marks = st.tabs(["⚙️ Setup Assignments", "✏️ Enter Marks"])

    with tab_setup:
        section_header("Scoring Method")
        with st.form("asgn_cfg_form"):
            method = st.radio(
                "Assignment scoring method",
                ["equal", "weighted", "best_of"],
                index=["equal","weighted","best_of"].index(asgn_cfg.get("method","equal")),
                format_func=lambda x: {
                    "equal":    "Equal weight (sum all)",
                    "weighted": "Custom weights per assignment",
                    "best_of":  "Best of N assignments",
                }[x],
                horizontal=True,
            )
            best_of_n = None
            if method == "best_of":
                best_of_n = st.number_input("Best of N", min_value=1,
                                             max_value=max(len(asgns),1),
                                             value=int(asgn_cfg.get("best_of_n") or 1), step=1)
            if st.form_submit_button("Save Method", use_container_width=True):
                GradingService.save_assignment_config(course_uuid, method, best_of_n)
                st.success("✅ Saved.")
                st.rerun()

        st.divider()
        section_header("Assignments", f"{len(asgns)} defined")

        with st.form("add_asgn_form"):
            c1, c2, c3, c4, c5 = st.columns([3,1,1,2,1])
            a_title  = c1.text_input("Title",       placeholder="Assignment 1")
            a_total  = c2.number_input("Out of",    min_value=1.0, value=10.0, step=1.0)
            a_weight = c3.number_input("Weight",    min_value=0.0, value=0.0,  step=0.5,
                                        help="0 = equal weight")
            a_clo    = c4.text_input("CLO (optional)")
            a_order  = c5.number_input("Order", min_value=1, value=len(asgns)+1, step=1)
            if st.form_submit_button("➕ Add Assignment", use_container_width=True):
                if not a_title:
                    st.error("Title required.")
                else:
                    ok = GradingService.add_assignment(
                        course_uuid, a_title, a_total,
                        a_weight if a_weight > 0 else None,
                        a_clo, a_order
                    )
                    if ok:
                        st.success(f"✅ '{a_title}' added.")
                        st.rerun()

        if asgns:
            for a in asgns:
                with st.expander(f"📄 {a['title']} — out of {a['total_marks']}"):
                    with st.form(f"edit_asgn_{a['id']}"):
                        c1, c2, c3, c4 = st.columns([3,1,1,2])
                        new_title  = c1.text_input("Title",  value=a["title"])
                        new_total  = c2.number_input("Out of", value=float(a["total_marks"]))
                        new_weight = c3.number_input("Weight", value=float(a["weight"] or 0))
                        new_clo    = c4.text_input("CLO", value=a.get("clo_no",""))
                        s1, s2 = st.columns(2)
                        if s1.form_submit_button("💾 Save"):
                            GradingService.update_assignment(a["id"], {
                                "title": new_title, "total_marks": new_total,
                                "weight": new_weight if new_weight > 0 else None,
                                "clo_no": new_clo,
                            })
                            st.success("✅ Updated.")
                            st.rerun()
                        if s2.form_submit_button("🗑️ Delete", type="secondary"):
                            GradingService.delete_assignment(a["id"])
                            st.warning("Deleted.")
                            st.rerun()

    with tab_marks:
        if not asgns:
            st.info("Add assignments in the Setup tab first.")
            return
        if not students:
            st.info("No students enrolled.")
            return

        sel_asgn_label = st.selectbox(
            "Select Assignment",
            [f"{a['title']} (/{a['total_marks']})" for a in asgns],
            key="sel_asgn"
        )
        sel_asgn = asgns[[f"{a['title']} (/{a['total_marks']})"
                           for a in asgns].index(sel_asgn_label)]

        entry_mode = st.radio("Entry mode", ["📋 Table (bulk)", "👤 Individual"],
                               horizontal=True, key="asgn_entry_mode")

        existing_marks = {
            m["student_id"]: m["obtained"]
            for m in GradingService.get_assignment_marks(sel_asgn["id"])
        }

        if entry_mode == "📋 Table (bulk)":
            _render_bulk_marks_table(
                students, existing_marks,
                float(sel_asgn["total_marks"]),
                save_fn=lambda sid, val: GradingService.save_assignment_mark(
                    sel_asgn["id"], sid, val),
                key_prefix=f"asgn_{sel_asgn['id']}"
            )
        else:
            _render_individual_marks(
                students, existing_marks,
                float(sel_asgn["total_marks"]),
                save_fn=lambda sid, val: GradingService.save_assignment_mark(
                    sel_asgn["id"], sid, val),
                key_prefix=f"asgn_ind_{sel_asgn['id']}"
            )


# ── Exam manager (midterm / final) ────────────────────────────────

def render_exam_manager(course_uuid: str, students: list,
                         exam_type: str = "midterm") -> None:
    """exam_type: 'midterm' or 'final'"""
    label   = "Midterm" if exam_type == "midterm" else "Final"
    get_fn  = GradingService.get_midterm    if exam_type == "midterm" \
              else GradingService.get_final
    cre_fn  = GradingService.create_midterm if exam_type == "midterm" \
              else GradingService.create_final
    get_q   = GradingService.get_midterm_questions if exam_type == "midterm" \
              else GradingService.get_final_questions
    add_q   = GradingService.add_midterm_question  if exam_type == "midterm" \
              else GradingService.add_final_question
    del_q   = GradingService.delete_midterm_question if exam_type == "midterm" \
              else GradingService.delete_final_question
    get_m   = GradingService.get_midterm_marks if exam_type == "midterm" \
              else GradingService.get_final_marks
    save_m  = GradingService.save_midterm_mark if exam_type == "midterm" \
              else GradingService.save_final_mark
    get_qm_fn  = GradingService.get_midterm_question_marks if exam_type == "midterm" \
                 else GradingService.get_final_question_marks
    save_qm_fn = GradingService.save_midterm_question_mark if exam_type == "midterm" \
                 else GradingService.save_final_question_mark

    exam = get_fn(course_uuid)

    tab_setup, tab_marks = st.tabs([f"⚙️ Setup {label}", f"✏️ Enter Marks"])

    # ── Setup ──────────────────────────────────────────────────────
    with tab_setup:
        if not exam:
            section_header(f"Configure {label} Exam")
            st.info(f"No {label.lower()} exam configured yet.")
            with st.form(f"{exam_type}_setup_form"):
                mode = st.radio(
                    "Entry mode",
                    ["total", "question"],
                    format_func=lambda x: "Enter total score directly" if x == "total"
                                          else "Enter question-by-question scores",
                    horizontal=True,
                )
                total_marks = st.number_input(
                    "Total marks (full exam)", min_value=1.0, value=100.0, step=1.0
                )
                if st.form_submit_button(f"Create {label} Exam", use_container_width=True):
                    result = cre_fn(course_uuid, mode, total_marks)
                    if result:
                        st.success(f"✅ {label} exam created.")
                        st.rerun()
                    else:
                        st.error("❌ Failed.")
        else:
            st.markdown(
                f"**Mode:** {'Total score' if exam['entry_mode'] == 'total' else 'Question-wise'} "
                f"| **Total marks:** {exam['total_marks']}"
            )

            if exam["entry_mode"] == "question":
                st.divider()
                section_header("Questions")
                questions = get_q(exam["id"])

                with st.form(f"add_{exam_type}_q_form"):
                    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
                    q_no     = c1.number_input("Q#",      min_value=1,
                                                value=len(questions)+1, step=1)
                    q_clo    = c2.text_input("CLO (optional)", placeholder="CLO-1")
                    q_total  = c3.number_input("Marks",   min_value=0.5, value=5.0, step=0.5)
                    q_order  = c4.number_input("Order",   min_value=1,
                                                value=len(questions)+1, step=1)
                    if st.form_submit_button("➕ Add Question", use_container_width=True):
                        ok = add_q(exam["id"], q_no, q_clo, q_total, q_order)
                        if ok:
                            st.success(f"✅ Q{q_no} added.")
                            st.rerun()

                if questions:
                    total_q_marks = sum(float(q["total_marks"]) for q in questions)
                    st.caption(
                        f"{len(questions)} question(s) · Total: {total_q_marks} marks"
                    )
                    for q in questions:
                        with st.expander(
                            f"Q{q['question_no']} — {q['total_marks']} marks"
                            + (f" | CLO: {q['clo_no']}" if q.get("clo_no") else "")
                        ):
                            if st.button("🗑️ Delete", key=f"del_q_{q['id']}"):
                                del_q(q["id"])
                                st.rerun()

            # Delete exam
            st.divider()
            if st.button(f"🗑️ Delete {label} Exam Configuration",
                          type="secondary", key=f"del_{exam_type}"):
                table = "midterm_exams" if exam_type == "midterm" else "final_exams"
                from services.supabase_client import supabase
                supabase.table(table).delete().eq("id", exam["id"]).execute()
                st.warning(f"{label} exam deleted.")
                st.rerun()

    # ── Marks entry ────────────────────────────────────────────────
    with tab_marks:
        if not exam:
            st.info(f"Configure the {label.lower()} exam in the Setup tab first.")
            return
        if not students:
            st.info("No students enrolled.")
            return

        if exam["entry_mode"] == "total":
            existing = {
                m["student_id"]: m["total_obtained"]
                for m in get_m(exam["id"])
            }
            entry_mode_ui = st.radio("Entry mode",
                                      ["📋 Table (bulk)", "👤 Individual"],
                                      horizontal=True, key=f"{exam_type}_entry_mode")
            if entry_mode_ui == "📋 Table (bulk)":
                _render_bulk_marks_table(
                    students, existing, float(exam["total_marks"]),
                    save_fn=lambda sid, val: save_m(exam["id"], sid, val),
                    key_prefix=f"{exam_type}_{exam['id']}"
                )
            else:
                _render_individual_marks(
                    students, existing, float(exam["total_marks"]),
                    save_fn=lambda sid, val: save_m(exam["id"], sid, val),
                    key_prefix=f"{exam_type}_ind_{exam['id']}"
                )

        else:  # question-wise
            questions = get_q(exam["id"])
            if not questions:
                st.info("Add questions in the Setup tab first.")
                return

            sel_student_label = st.selectbox(
                "Select Student",
                [f"{_student_display_name(s['profiles'])} — {s['profiles'].get('enrollment_number','')}"
                 for s in students],
                key=f"{exam_type}_sel_student"
            )
            sel_student = students[
                [f"{_student_display_name(s['profiles'])} — {s['profiles'].get('enrollment_number','')}"
                 for s in students].index(sel_student_label)
            ]
            sid = sel_student["profiles"]["id"]

            existing_qmarks = {
                qm["question_id"]: qm["obtained"]
                for qm in get_qm_fn(exam["id"], sid)
            }

            st.markdown(f"**Student:** {_student_display_name(sel_student['profiles'])}")

            with st.form(f"{exam_type}_qmarks_{sid}"):
                total_obtained = 0.0
                entries = {}
                for q in questions:
                    current = existing_qmarks.get(q["id"])
                    clo_tag = f" | CLO: {q['clo_no']}" if q.get("clo_no") else ""
                    val = st.number_input(
                        f"Q{q['question_no']} — out of {q['total_marks']}{clo_tag}",
                        min_value=0.0, max_value=float(q["total_marks"]),
                        value=float(current) if current is not None else 0.0,
                        step=0.5, key=f"{exam_type}_q_{q['id']}_{sid}"
                    )
                    entries[q["id"]] = val
                    total_obtained += val

                st.caption(
                    f"Total obtained: **{total_obtained}** / {exam['total_marks']}"
                )
                if st.form_submit_button("💾 Save All Questions", use_container_width=True):
                    all_ok = True
                    for q_id, val in entries.items():
                        ok = save_qm_fn(exam["id"], q_id, sid, val)
                        if not ok:
                            all_ok = False
                    if all_ok:
                        st.success("✅ All question marks saved.")
                    else:
                        st.error("❌ Some marks failed to save.")


# ── Shared marks entry helpers ────────────────────────────────────

def _render_bulk_marks_table(
    students: list,
    existing_marks: dict,
    max_marks: float,
    save_fn,
    key_prefix: str,
) -> None:
    """Spreadsheet-style bulk marks entry."""
    section_header("Bulk Entry", f"Out of {max_marks}")

    rows = []
    for e in students:
        p   = e["profiles"]
        sid = p["id"]
        rows.append({
            "student_id":     sid,
            "Name":           _student_display_name(p),
            "Enrollment No":  p.get("enrollment_number","—"),
            "Obtained":       float(existing_marks.get(sid) or 0.0),
        })

    df = pd.DataFrame(rows)

    edited = st.data_editor(
        df[["Name","Enrollment No","Obtained"]],
        column_config={
            "Name":          st.column_config.TextColumn(disabled=True),
            "Enrollment No": st.column_config.TextColumn(disabled=True),
            "Obtained":      st.column_config.NumberColumn(
                                 f"Marks (/{max_marks})",
                                 min_value=0.0, max_value=max_marks, step=0.5,
                             ),
        },
        use_container_width=True,
        hide_index=True,
        key=f"editor_{key_prefix}",
    )

    if st.button("💾 Save All Marks", key=f"save_bulk_{key_prefix}",
                  type="primary", use_container_width=True):
        saved, failed = 0, 0
        for i, row in edited.iterrows():
            sid = df.iloc[i]["student_id"]
            ok  = save_fn(sid, float(row["Obtained"]))
            if ok:
                saved += 1
            else:
                failed += 1
        if failed == 0:
            st.success(f"✅ Marks saved for {saved} student(s).")
        else:
            st.warning(f"⚠️ Saved: {saved}, Failed: {failed}")


def _render_individual_marks(
    students: list,
    existing_marks: dict,
    max_marks: float,
    save_fn,
    key_prefix: str,
) -> None:
    """Per-student marks entry."""
    section_header("Individual Entry", f"Out of {max_marks}")

    for e in students:
        p   = e["profiles"]
        sid = p["id"]
        name = _student_display_name(p)
        current = existing_marks.get(sid)
        with st.container():
            c1, c2, c3 = st.columns([4, 2, 1])
            c1.write(f"**{name}**  `{p.get('enrollment_number','')}`")
            new_val = c2.number_input(
                f"/{max_marks}", min_value=0.0, max_value=max_marks,
                value=float(current) if current is not None else 0.0,
                step=0.5, label_visibility="collapsed",
                key=f"{key_prefix}_{sid}"
            )
            if c3.button("💾", key=f"save_ind_{key_prefix}_{sid}",
                          help="Save this student's mark"):
                if save_fn(sid, new_val):
                    st.toast(f"✅ Saved: {name}", icon="✅")
                else:
                    st.toast(f"❌ Failed: {name}", icon="❌")
        st.divider()


# ── Gradebook summary ─────────────────────────────────────────────

def render_gradebook_summary(course_uuid: str, students: list,
                               can_submit: bool = True,
                               can_approve: bool = False) -> None:
    scheme = GradingService.get_effective_scheme(course_uuid)

    section_header("Compile & Review Grades")

    col1, col2 = st.columns(2)
    if col1.button("🔄 Compile All Grades", use_container_width=True, type="primary"):
        student_profiles = [{"id": e["profiles"]["id"]} for e in students]
        with st.spinner("Compiling grades..."):
            ok, msg = GradingService.compile_grades(course_uuid, student_profiles)
        if ok:
            st.success(f"✅ {msg}")
            st.rerun()
        else:
            st.error(f"❌ {msg}")

    compiled = GradingService.get_compiled_grades(course_uuid)

    if not compiled:
        st.info("No compiled grades yet. Click Compile to generate.")
        return

    st.divider()

    # Summary table
    rows = []
    for g in compiled:
        p       = g.get("profiles", {}) or {}
        letter  = g.get("letter_grade") or "—"
        total   = g.get("total_score")
        suggs   = suggest_grade_change(total, scheme) if total is not None else []
        rows.append({
            "Name":         _student_display_name(p),
            "Enroll No":    p.get("enrollment_number","—"),
            "Quiz":         f"{g.get('quiz_score','—')}",
            "Assignment":   f"{g.get('assignment_score','—')}",
            "Midterm":      f"{g.get('midterm_score','—')}",
            "Final":        f"{g.get('final_score','—')}",
            "Total":        f"{total:.2f}" if total is not None else "—",
            "Grade":        f"{_grade_colour(letter)} {letter}",
            "Suggestions":  " | ".join(suggs) if suggs else "—",
            "Status":       g.get("status","—").capitalize(),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Grade distribution
    st.divider()
    section_header("Grade Distribution")
    grade_counts = {}
    for g in compiled:
        l = g.get("letter_grade") or "—"
        grade_counts[l] = grade_counts.get(l, 0) + 1
    dist_df = pd.DataFrame(
        [{"Grade": k, "Count": v} for k, v in sorted(grade_counts.items())]
    )
    st.bar_chart(dist_df.set_index("Grade"))

    # Status actions
    st.divider()
    statuses = {g["status"] for g in compiled}

    if can_submit and "draft" in statuses:
        if st.button("📤 Submit Grades for Approval", use_container_width=True,
                      type="primary"):
            if GradingService.submit_grades(course_uuid):
                st.success("✅ Grades submitted for admin approval.")
                st.rerun()
            else:
                st.error("❌ Submission failed.")

    if can_approve:
        if "submitted" in statuses:
            c1, c2 = st.columns(2)
            if c1.button("✅ Approve Grades", use_container_width=True, type="primary"):
                if GradingService.approve_grades(course_uuid):
                    st.success("✅ Grades approved.")
                    st.rerun()
            if c2.button("📢 Approve & Release to Students",
                          use_container_width=True):
                if GradingService.approve_grades(course_uuid):
                    GradingService.release_grades(course_uuid)
                    st.success("✅ Grades approved and released to students.")
                    st.rerun()

        if "approved" in statuses:
            if st.button("📢 Release Grades to Students",
                          use_container_width=True, type="primary"):
                if GradingService.release_grades(course_uuid):
                    st.success("✅ Grades released.")
                    st.rerun()
