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


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _student_display_name(profile: dict) -> str:
    full = (profile.get("full_name") or "").strip()
    if full:
        return full
    first = (profile.get("first_name") or "").strip()
    last  = (profile.get("last_name")  or "").strip()
    return f"{first} {last}".strip() or profile.get("enrollment_number", "—")


def _grade_colour(letter: str) -> str:
    if not letter:   return ""
    if letter.startswith("A"): return "🟢"
    if letter.startswith("B"): return "🔵"
    if letter.startswith("C"): return "🟡"
    if letter.startswith("D"): return "🟠"
    return "🔴"


def _item_card(col, icon: str, title: str, subtitle: str, key: str) -> bool:
    col.markdown(f"""
    <div style="background:#ffffff;border:1.5px solid #e2ecf0;border-radius:12px;
                padding:1.1rem 0.9rem 0.7rem;text-align:center;
                box-shadow:0 2px 8px rgba(48,120,144,0.07);margin-bottom:0.3rem;">
        <div style="font-size:1.9rem;margin-bottom:0.25rem;">{icon}</div>
        <div style="font-size:0.88rem;font-weight:700;color:#186078;">{title}</div>
        <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)
    return col.button("Open", key=f"tile_{key}", use_container_width=True)


# ─────────────────────────────────────────────────────────────────
# SCHEME EDITOR
# ─────────────────────────────────────────────────────────────────

def render_scheme_editor(course_uuid: str, is_admin: bool = False) -> None:
    scheme        = GradingService.get_effective_scheme(course_uuid)
    is_overridden = scheme.get("course_id") is not None

    st.markdown(f"**Using:** {'📌 Course override' if is_overridden else '🌐 Global scheme'}")
    if is_overridden and st.button("↩️ Reset to Global Scheme", key="reset_scheme"):
        if GradingService.reset_course_scheme(course_uuid):
            st.success("✅ Reset to global scheme.")
            st.rerun()

    with st.expander("⚙️ Edit Grading Scheme" + (" (Admin: also edits global)" if is_admin else ""), expanded=False):
        with st.form("scheme_form"):
            section_header("Component Weights", "Must sum to 100")
            c1,c2,c3,c4 = st.columns(4)
            w_quiz = c1.number_input("Quiz %",       min_value=0.0, max_value=100.0, value=float(scheme["weight_quiz"]),       step=1.0)
            w_asgn = c2.number_input("Assignment %", min_value=0.0, max_value=100.0, value=float(scheme["weight_assignment"]),  step=1.0)
            w_mid  = c3.number_input("Midterm %",    min_value=0.0, max_value=100.0, value=float(scheme["weight_midterm"]),     step=1.0)
            w_fin  = c4.number_input("Final %",      min_value=0.0, max_value=100.0, value=float(scheme["weight_final"]),       step=1.0)
            st.divider()
            section_header("Letter Grade Thresholds", "Lower bound of each grade")
            r1c1,r1c2,r1c3,r1c4,r1c5 = st.columns(5)
            g_a  = r1c1.number_input("A ≥",  value=float(scheme["grade_a_min"]),   step=1.0)
            g_am = r1c2.number_input("A- ≥", value=float(scheme["grade_a_m_min"]), step=1.0)
            g_bp = r1c3.number_input("B+ ≥", value=float(scheme["grade_bp_min"]),  step=1.0)
            g_b  = r1c4.number_input("B ≥",  value=float(scheme["grade_b_min"]),   step=1.0)
            g_bm = r1c5.number_input("B- ≥", value=float(scheme["grade_b_m_min"]), step=1.0)
            r2c1,r2c2,r2c3,r2c4,r2c5 = st.columns(5)
            g_cp = r2c1.number_input("C+ ≥", value=float(scheme["grade_cp_min"]),  step=1.0)
            g_c  = r2c2.number_input("C ≥",  value=float(scheme["grade_c_min"]),   step=1.0)
            g_cm = r2c3.number_input("C- ≥", value=float(scheme["grade_c_m_min"]), step=1.0)
            g_dp = r2c4.number_input("D+ ≥", value=float(scheme["grade_dp_min"]),  step=1.0)
            g_d  = r2c5.number_input("D ≥",  value=float(scheme["grade_d_min"]),   step=1.0)
            st.caption("F = anything below D threshold")
            save_global = st.checkbox("Also update the Global Scheme", value=False, disabled=not is_admin) if is_admin else False
            submitted = st.form_submit_button("💾 Save Scheme", use_container_width=True)
        if submitted:
            total_w = w_quiz + w_asgn + w_mid + w_fin
            if round(total_w) != 100:
                st.error(f"Weights must sum to 100. Current sum: {total_w}")
            else:
                data = {"weight_quiz":w_quiz,"weight_assignment":w_asgn,"weight_midterm":w_mid,"weight_final":w_fin,
                        "grade_a_min":g_a,"grade_a_m_min":g_am,"grade_bp_min":g_bp,"grade_b_min":g_b,"grade_b_m_min":g_bm,
                        "grade_cp_min":g_cp,"grade_c_min":g_c,"grade_c_m_min":g_cm,"grade_dp_min":g_dp,"grade_d_min":g_d}
                ok = GradingService.save_course_scheme(course_uuid, data.copy())
                if is_admin and save_global:
                    GradingService.update_global_scheme(data.copy())
                if ok:
                    st.success("✅ Scheme saved.")
                    st.rerun()
                else:
                    st.error("❌ Save failed.")


# ─────────────────────────────────────────────────────────────────
# QUIZ MANAGER
# ─────────────────────────────────────────────────────────────────

def render_quiz_manager(course_uuid: str, students: list) -> None:
    quizzes  = GradingService.get_quizzes(course_uuid)
    quiz_cfg = GradingService.get_quiz_config(course_uuid)

    ADD_KEY   = f"quiz_add_{course_uuid}"
    MARKS_KEY = f"quiz_marks_{course_uuid}"
    EDIT_KEY  = f"quiz_edit_{course_uuid}"

    with st.expander("⚙️ Scoring Method", expanded=False):
        _render_quiz_scoring_config(course_uuid, quizzes, quiz_cfg)

    st.divider()
    section_header("Quizzes", f"{len(quizzes)} configured")

    cols = st.columns(4)
    if _item_card(cols[0], "➕", "Add Quiz", "Create a new quiz", f"add_quiz_{course_uuid}"):
        st.session_state[ADD_KEY] = True
        st.session_state.pop(MARKS_KEY, None)

    for idx, q in enumerate(quizzes):
        col = cols[(idx + 1) % 4]
        mc  = len(GradingService.get_quiz_marks(q["id"]))
        if _item_card(col, "📝", q["title"], f"/{q['total_marks']}  ·  {mc} marks entered", f"qtile_{q['id']}"):
            st.session_state[MARKS_KEY] = q["id"]
            st.session_state.pop(ADD_KEY, None)
            st.session_state.pop(EDIT_KEY, None)

    # Add form
    if st.session_state.get(ADD_KEY):
        st.markdown("---")
        st.markdown("### ➕ Add Quiz")
        with st.form(f"add_quiz_form_{course_uuid}", clear_on_submit=True):
            fc1,fc2 = st.columns([3,1])
            q_title = fc1.text_input("Quiz Title *", placeholder="e.g. Quiz 1")
            q_total = fc2.number_input("Out of *", min_value=1.0, value=10.0, step=1.0)
            fc3,fc4 = st.columns([3,1])
            q_clo   = fc3.text_input("CLO (optional)", placeholder="e.g. CLO-1")
            q_order = fc4.number_input("Display Order", min_value=1, value=len(quizzes)+1, step=1)
            q_weight = None
            if quiz_cfg.get("method") == "weighted":
                q_weight = st.number_input("Weight for this quiz", min_value=0.01, max_value=100.0, value=1.0, step=0.5, help="Relative weight vs other quizzes.")
            sc1,sc2 = st.columns(2)
            save   = sc1.form_submit_button("💾 Save Quiz", use_container_width=True)
            cancel = sc2.form_submit_button("✖ Cancel",    use_container_width=True)
        if save:
            if not q_title.strip():
                st.error("Quiz title is required.")
            else:
                if GradingService.add_quiz(course_uuid, q_title.strip(), q_total, q_weight, q_clo.strip() or None, int(q_order)):
                    st.success(f"✅ '{q_title}' added.")
                    st.session_state.pop(ADD_KEY, None)
                    st.rerun()
                else:
                    st.error("❌ Failed to add quiz.")
        if cancel:
            st.session_state.pop(ADD_KEY, None)
            st.rerun()

    # Active quiz panel
    active_qid = st.session_state.get(MARKS_KEY)
    if active_qid:
        quiz = next((q for q in quizzes if q["id"] == active_qid), None)
        if not quiz:
            st.session_state.pop(MARKS_KEY, None)
            st.rerun()

        st.markdown("---")
        qh1,qh2 = st.columns([5,1])
        qh1.markdown(f"### 📝 {quiz['title']}  `/{quiz['total_marks']}`")
        if qh2.button("✖ Close", key=f"close_quiz_{active_qid}"):
            st.session_state.pop(MARKS_KEY, None)
            st.session_state.pop(EDIT_KEY, None)
            st.rerun()

        ac = st.columns(3)
        if ac[0].button("✏️ Edit Quiz",   key=f"edit_q_{active_qid}", use_container_width=True):
            st.session_state[EDIT_KEY] = active_qid
        if ac[2].button("🗑️ Delete Quiz", key=f"del_q_{active_qid}",  use_container_width=True):
            st.session_state[f"cdq_{active_qid}"] = True

        if st.session_state.get(f"cdq_{active_qid}"):
            st.warning(f"⚠️ Delete **{quiz['title']}** and all its marks?")
            cy,cn = st.columns(2)
            if cy.button("Yes, Delete", key=f"ydq_{active_qid}", use_container_width=True):
                GradingService.delete_quiz(active_qid)
                st.session_state.pop(MARKS_KEY, None)
                st.session_state.pop(f"cdq_{active_qid}", None)
                st.rerun()
            if cn.button("Cancel", key=f"ndq_{active_qid}", use_container_width=True):
                st.session_state.pop(f"cdq_{active_qid}", None)
                st.rerun()

        if st.session_state.get(EDIT_KEY) == active_qid:
            with st.form(f"edit_quiz_form_{active_qid}"):
                st.markdown("**✏️ Edit Quiz**")
                ec1,ec2 = st.columns([3,1])
                new_title = ec1.text_input("Title",  value=quiz["title"])
                new_total = ec2.number_input("Out of", value=float(quiz["total_marks"]), min_value=1.0, step=1.0)
                new_clo   = st.text_input("CLO", value=quiz.get("clo_no","") or "")
                new_weight = None
                if quiz_cfg.get("method") == "weighted":
                    new_weight = st.number_input("Weight", value=float(quiz.get("weight") or 1.0), min_value=0.01, step=0.5)
                es1,es2 = st.columns(2)
                esave   = es1.form_submit_button("💾 Save",   use_container_width=True)
                ecancel = es2.form_submit_button("✖ Cancel", use_container_width=True)
            if esave:
                GradingService.update_quiz(active_qid, {"title":new_title,"total_marks":new_total,"clo_no":new_clo or None,"weight":new_weight})
                st.session_state.pop(EDIT_KEY, None)
                st.success("✅ Updated.")
                st.rerun()
            if ecancel:
                st.session_state.pop(EDIT_KEY, None)
                st.rerun()

        st.markdown("#### ✏️ Enter Marks")
        if not students:
            st.info("No students enrolled in this course.")
        else:
            entry_mode = st.radio("Entry mode", ["📋 Table (bulk)", "👤 Individual"], horizontal=True, key=f"quiz_entry_{active_qid}")
            existing_marks = {m["student_id"]: m["obtained"] for m in GradingService.get_quiz_marks(active_qid)}
            if entry_mode == "📋 Table (bulk)":
                _render_bulk_marks_table(students, existing_marks, float(quiz["total_marks"]),
                    save_fn=lambda sid, val: GradingService.save_quiz_mark(active_qid, sid, val),
                    key_prefix=f"quiz_{active_qid}")
            else:
                _render_individual_marks(students, existing_marks, float(quiz["total_marks"]),
                    save_fn=lambda sid, val: GradingService.save_quiz_mark(active_qid, sid, val),
                    key_prefix=f"quiz_ind_{active_qid}")


def _render_quiz_scoring_config(course_uuid: str, quizzes: list, quiz_cfg: dict) -> None:
    current_method = quiz_cfg.get("method", "equal")
    current_bon    = int(quiz_cfg.get("best_of_n") or 1)
    total_quizzes  = len(quizzes)
    st.markdown("**Choose how quiz scores are combined into a single quiz grade:**")
    with st.form("quiz_cfg_form"):
        method = st.radio("Scoring method", ["equal","weighted","best_of"],
            index=["equal","weighted","best_of"].index(current_method),
            format_func=lambda x: {"equal":"📊 Equal Weight — every quiz counts equally","weighted":"⚖️ Weighted — each quiz has its own custom weight","best_of":"🏆 Best of N — only the top N scores count"}[x],
            key="quiz_method_radio")
        best_of_n = current_bon
        if method == "equal":
            st.info("All quizzes carry equal weight. Final quiz score = (sum of obtained) ÷ (sum of totals) × 100.")
        elif method == "weighted":
            st.info("Each quiz has its own weight set per quiz. Final score = Σ(obtained/total × weight) ÷ Σ(weights) × 100. Higher weight = more impact.")
        elif method == "best_of":
            st.info("Only the student's top N quiz scores count. Lower or missed quizzes are dropped automatically.")
            best_of_n = st.selectbox("Count the best ___ quizzes",
                options=list(range(1, max(total_quizzes, 2) + 1)),
                index=min(current_bon - 1, max(total_quizzes - 1, 0)),
                format_func=lambda n: f"Best {n} of {total_quizzes} quiz(es)",
                key="quiz_bon_select")
        if st.form_submit_button("💾 Save Scoring Method", use_container_width=True):
            GradingService.save_quiz_config(course_uuid, method, best_of_n if method == "best_of" else None)
            st.success("✅ Scoring method saved.")
            st.rerun()


# ─────────────────────────────────────────────────────────────────
# ASSIGNMENT MANAGER
# ─────────────────────────────────────────────────────────────────

def render_assignment_manager(course_uuid: str, students: list) -> None:
    asgns    = GradingService.get_assignments(course_uuid)
    asgn_cfg = GradingService.get_assignment_config(course_uuid)

    ADD_KEY   = f"asgn_add_{course_uuid}"
    MARKS_KEY = f"asgn_marks_{course_uuid}"
    EDIT_KEY  = f"asgn_edit_{course_uuid}"

    with st.expander("⚙️ Scoring Method", expanded=False):
        _render_assignment_scoring_config(course_uuid, asgns, asgn_cfg)

    st.divider()
    section_header("Assignments", f"{len(asgns)} configured")

    cols = st.columns(4)
    if _item_card(cols[0], "➕", "Add Assignment", "Create a new assignment", f"add_asgn_{course_uuid}"):
        st.session_state[ADD_KEY] = True
        st.session_state.pop(MARKS_KEY, None)

    for idx, a in enumerate(asgns):
        col = cols[(idx + 1) % 4]
        mc  = len(GradingService.get_assignment_marks(a["id"]))
        if _item_card(col, "📄", a["title"], f"/{a['total_marks']}  ·  {mc} marks entered", f"atile_{a['id']}"):
            st.session_state[MARKS_KEY] = a["id"]
            st.session_state.pop(ADD_KEY, None)
            st.session_state.pop(EDIT_KEY, None)

    if st.session_state.get(ADD_KEY):
        st.markdown("---")
        st.markdown("### ➕ Add Assignment")
        with st.form(f"add_asgn_form_{course_uuid}", clear_on_submit=True):
            fc1,fc2 = st.columns([3,1])
            a_title = fc1.text_input("Assignment Title *", placeholder="e.g. Assignment 1")
            a_total = fc2.number_input("Out of *", min_value=1.0, value=10.0, step=1.0)
            fc3,fc4 = st.columns([3,1])
            a_clo   = fc3.text_input("CLO (optional)", placeholder="e.g. CLO-2")
            a_order = fc4.number_input("Display Order", min_value=1, value=len(asgns)+1, step=1)
            a_weight = None
            if asgn_cfg.get("method") == "weighted":
                a_weight = st.number_input("Weight for this assignment", min_value=0.01, max_value=100.0, value=1.0, step=0.5, help="Relative weight vs other assignments.")
            sc1,sc2 = st.columns(2)
            save   = sc1.form_submit_button("💾 Save Assignment", use_container_width=True)
            cancel = sc2.form_submit_button("✖ Cancel",           use_container_width=True)
        if save:
            if not a_title.strip():
                st.error("Assignment title is required.")
            else:
                if GradingService.add_assignment(course_uuid, a_title.strip(), a_total, a_weight, a_clo.strip() or None, int(a_order)):
                    st.success(f"✅ '{a_title}' added.")
                    st.session_state.pop(ADD_KEY, None)
                    st.rerun()
                else:
                    st.error("❌ Failed.")
        if cancel:
            st.session_state.pop(ADD_KEY, None)
            st.rerun()

    active_aid = st.session_state.get(MARKS_KEY)
    if active_aid:
        asgn = next((a for a in asgns if a["id"] == active_aid), None)
        if not asgn:
            st.session_state.pop(MARKS_KEY, None)
            st.rerun()

        st.markdown("---")
        ah1,ah2 = st.columns([5,1])
        ah1.markdown(f"### 📄 {asgn['title']}  `/{asgn['total_marks']}`")
        if ah2.button("✖ Close", key=f"close_asgn_{active_aid}"):
            st.session_state.pop(MARKS_KEY, None)
            st.session_state.pop(EDIT_KEY, None)
            st.rerun()

        ac = st.columns(3)
        if ac[0].button("✏️ Edit Assignment",   key=f"edit_a_{active_aid}", use_container_width=True):
            st.session_state[EDIT_KEY] = active_aid
        if ac[2].button("🗑️ Delete Assignment", key=f"del_a_{active_aid}",  use_container_width=True):
            st.session_state[f"cda_{active_aid}"] = True

        if st.session_state.get(f"cda_{active_aid}"):
            st.warning(f"⚠️ Delete **{asgn['title']}** and all its marks?")
            cy,cn = st.columns(2)
            if cy.button("Yes, Delete", key=f"yda_{active_aid}", use_container_width=True):
                GradingService.delete_assignment(active_aid)
                st.session_state.pop(MARKS_KEY, None)
                st.session_state.pop(f"cda_{active_aid}", None)
                st.rerun()
            if cn.button("Cancel", key=f"nda_{active_aid}", use_container_width=True):
                st.session_state.pop(f"cda_{active_aid}", None)
                st.rerun()

        if st.session_state.get(EDIT_KEY) == active_aid:
            with st.form(f"edit_asgn_form_{active_aid}"):
                st.markdown("**✏️ Edit Assignment**")
                ec1,ec2 = st.columns([3,1])
                new_title = ec1.text_input("Title",  value=asgn["title"])
                new_total = ec2.number_input("Out of", value=float(asgn["total_marks"]), min_value=1.0, step=1.0)
                new_clo   = st.text_input("CLO", value=asgn.get("clo_no","") or "")
                new_weight = None
                if asgn_cfg.get("method") == "weighted":
                    new_weight = st.number_input("Weight", value=float(asgn.get("weight") or 1.0), min_value=0.01, step=0.5)
                es1,es2 = st.columns(2)
                esave   = es1.form_submit_button("💾 Save",   use_container_width=True)
                ecancel = es2.form_submit_button("✖ Cancel", use_container_width=True)
            if esave:
                GradingService.update_assignment(active_aid, {"title":new_title,"total_marks":new_total,"clo_no":new_clo or None,"weight":new_weight})
                st.session_state.pop(EDIT_KEY, None)
                st.success("✅ Updated.")
                st.rerun()
            if ecancel:
                st.session_state.pop(EDIT_KEY, None)
                st.rerun()

        st.markdown("#### ✏️ Enter Marks")
        if not students:
            st.info("No students enrolled in this course.")
        else:
            entry_mode = st.radio("Entry mode", ["📋 Table (bulk)", "👤 Individual"], horizontal=True, key=f"asgn_entry_{active_aid}")
            existing_marks = {m["student_id"]: m["obtained"] for m in GradingService.get_assignment_marks(active_aid)}
            if entry_mode == "📋 Table (bulk)":
                _render_bulk_marks_table(students, existing_marks, float(asgn["total_marks"]),
                    save_fn=lambda sid, val: GradingService.save_assignment_mark(active_aid, sid, val),
                    key_prefix=f"asgn_{active_aid}")
            else:
                _render_individual_marks(students, existing_marks, float(asgn["total_marks"]),
                    save_fn=lambda sid, val: GradingService.save_assignment_mark(active_aid, sid, val),
                    key_prefix=f"asgn_ind_{active_aid}")


def _render_assignment_scoring_config(course_uuid: str, asgns: list, asgn_cfg: dict) -> None:
    current_method = asgn_cfg.get("method", "equal")
    current_bon    = int(asgn_cfg.get("best_of_n") or 1)
    total_asgns    = len(asgns)
    st.markdown("**Choose how assignment scores are combined into a single assignment grade:**")
    with st.form("asgn_cfg_form"):
        method = st.radio("Scoring method", ["equal","weighted","best_of"],
            index=["equal","weighted","best_of"].index(current_method),
            format_func=lambda x: {"equal":"📊 Equal Weight — every assignment counts equally","weighted":"⚖️ Weighted — each assignment has its own custom weight","best_of":"🏆 Best of N — only the top N scores count"}[x],
            key="asgn_method_radio")
        best_of_n = current_bon
        if method == "equal":
            st.info("All assignments carry equal weight. Final score = (sum of obtained) ÷ (sum of totals) × 100.")
        elif method == "weighted":
            st.info("Each assignment has its own weight. Final score = Σ(obtained/total × weight) ÷ Σ(weights) × 100. Higher weight = more impact on the final grade.")
        elif method == "best_of":
            st.info("Only the student's top N assignment scores count. Lower or missed ones are dropped automatically.")
            best_of_n = st.selectbox("Count the best ___ assignments",
                options=list(range(1, max(total_asgns, 2) + 1)),
                index=min(current_bon - 1, max(total_asgns - 1, 0)),
                format_func=lambda n: f"Best {n} of {total_asgns} assignment(s)",
                key="asgn_bon_select")
        if st.form_submit_button("💾 Save Scoring Method", use_container_width=True):
            GradingService.save_assignment_config(course_uuid, method, best_of_n if method == "best_of" else None)
            st.success("✅ Scoring method saved.")
            st.rerun()


# ─────────────────────────────────────────────────────────────────
# EXAM MANAGER
# ─────────────────────────────────────────────────────────────────

def render_exam_manager(course_uuid: str, students: list, exam_type: str = "midterm") -> None:
    label      = "Midterm" if exam_type == "midterm" else "Final"
    get_fn     = GradingService.get_midterm    if exam_type == "midterm" else GradingService.get_final
    cre_fn     = GradingService.create_midterm if exam_type == "midterm" else GradingService.create_final
    get_q      = GradingService.get_midterm_questions if exam_type == "midterm" else GradingService.get_final_questions
    add_q      = GradingService.add_midterm_question  if exam_type == "midterm" else GradingService.add_final_question
    del_q      = GradingService.delete_midterm_question if exam_type == "midterm" else GradingService.delete_final_question
    get_m      = GradingService.get_midterm_marks if exam_type == "midterm" else GradingService.get_final_marks
    save_m     = GradingService.save_midterm_mark if exam_type == "midterm" else GradingService.save_final_mark
    get_qm_fn  = GradingService.get_midterm_question_marks if exam_type == "midterm" else GradingService.get_final_question_marks
    save_qm_fn = GradingService.save_midterm_question_mark if exam_type == "midterm" else GradingService.save_final_question_mark

    exam = get_fn(course_uuid)
    tab_setup, tab_marks = st.tabs([f"⚙️ Setup {label}", "✏️ Enter Marks"])

    with tab_setup:
        if not exam:
            section_header(f"Configure {label} Exam")
            st.info(f"No {label.lower()} exam configured yet.")
            with st.form(f"{exam_type}_setup_form"):
                mode = st.radio("Entry mode", ["total","question"],
                    format_func=lambda x: "Enter total score directly" if x=="total" else "Enter question-by-question scores",
                    horizontal=True)
                total_marks = st.number_input("Total marks (full exam)", min_value=1.0, value=100.0, step=1.0)
                if st.form_submit_button(f"Create {label} Exam", use_container_width=True):
                    if cre_fn(course_uuid, mode, total_marks):
                        st.success(f"✅ {label} exam created.")
                        st.rerun()
                    else:
                        st.error("❌ Failed.")
        else:
            st.markdown(f"**Mode:** {'Total score' if exam['entry_mode']=='total' else 'Question-wise'} | **Total marks:** {exam['total_marks']}")
            if exam["entry_mode"] == "question":
                st.divider()
                section_header("Questions")
                questions = get_q(exam["id"])
                with st.form(f"add_{exam_type}_q_form"):
                    c1,c2,c3,c4 = st.columns([1,2,1,1])
                    q_no    = c1.number_input("Q#",    min_value=1, value=len(questions)+1, step=1)
                    q_clo   = c2.text_input("CLO (optional)", placeholder="CLO-1")
                    q_total = c3.number_input("Marks", min_value=0.5, value=5.0, step=0.5)
                    q_order = c4.number_input("Order", min_value=1, value=len(questions)+1, step=1)
                    if st.form_submit_button("➕ Add Question", use_container_width=True):
                        if add_q(exam["id"], q_no, q_clo, q_total, q_order):
                            st.success(f"✅ Q{q_no} added.")
                            st.rerun()
                if questions:
                    total_q_marks = sum(float(q["total_marks"]) for q in questions)
                    st.caption(f"{len(questions)} question(s) · Total: {total_q_marks} marks")
                    for q in questions:
                        with st.expander(f"Q{q['question_no']} — {q['total_marks']} marks" + (f" | CLO: {q['clo_no']}" if q.get("clo_no") else "")):
                            if st.button("🗑️ Delete", key=f"del_q_{q['id']}"):
                                del_q(q["id"])
                                st.rerun()
            st.divider()
            if st.button(f"🗑️ Delete {label} Exam Configuration", type="secondary", key=f"del_{exam_type}"):
                table = "midterm_exams" if exam_type == "midterm" else "final_exams"
                from services.supabase_client import supabase
                supabase.table(table).delete().eq("id", exam["id"]).execute()
                st.warning(f"{label} exam deleted.")
                st.rerun()

    with tab_marks:
        if not exam:
            st.info(f"Configure the {label.lower()} exam in the Setup tab first.")
            return
        if not students:
            st.info("No students enrolled in this course.")
            return

        if exam["entry_mode"] == "total":
            existing = {m["student_id"]: m["total_obtained"] for m in get_m(exam["id"])}
            entry_mode_ui = st.radio("Entry mode", ["📋 Table (bulk)", "👤 Individual"], horizontal=True, key=f"{exam_type}_entry_mode")
            if entry_mode_ui == "📋 Table (bulk)":
                _render_bulk_marks_table(students, existing, float(exam["total_marks"]),
                    save_fn=lambda sid, val: save_m(exam["id"], sid, val),
                    key_prefix=f"{exam_type}_{exam['id']}")
            else:
                _render_individual_marks(students, existing, float(exam["total_marks"]),
                    save_fn=lambda sid, val: save_m(exam["id"], sid, val),
                    key_prefix=f"{exam_type}_ind_{exam['id']}")
        else:
            questions = get_q(exam["id"])
            if not questions:
                st.info("Add questions in the Setup tab first.")
                return
            student_labels = [f"{_student_display_name(s['profiles'])} — {s['profiles'].get('enrollment_number','')}" for s in students]
            sel_label   = st.selectbox("Select Student", student_labels, key=f"{exam_type}_sel_student")
            sel_student = students[student_labels.index(sel_label)]
            sid = sel_student["profiles"]["id"]
            existing_qmarks = {qm["question_id"]: qm["obtained"] for qm in get_qm_fn(exam["id"], sid)}
            st.markdown(f"**Student:** {_student_display_name(sel_student['profiles'])}")
            with st.form(f"{exam_type}_qmarks_{sid}"):
                total_obtained = 0.0
                entries = {}
                for q in questions:
                    current = existing_qmarks.get(q["id"])
                    clo_tag = f" | CLO: {q['clo_no']}" if q.get("clo_no") else ""
                    val = st.number_input(f"Q{q['question_no']} — out of {q['total_marks']}{clo_tag}",
                        min_value=0.0, max_value=float(q["total_marks"]),
                        value=float(current) if current is not None else 0.0,
                        step=0.5, key=f"{exam_type}_q_{q['id']}_{sid}")
                    entries[q["id"]] = val
                    total_obtained  += val
                st.caption(f"Total obtained: **{total_obtained}** / {exam['total_marks']}")
                if st.form_submit_button("💾 Save All Questions", use_container_width=True):
                    all_ok = all(save_qm_fn(exam["id"], q_id, sid, val) for q_id, val in entries.items())
                    if all_ok:
                        st.success("✅ All question marks saved.")
                    else:
                        st.error("❌ Some marks failed to save.")


# ─────────────────────────────────────────────────────────────────
# SHARED MARKS ENTRY HELPERS
# ─────────────────────────────────────────────────────────────────

def _render_bulk_marks_table(students, existing_marks, max_marks, save_fn, key_prefix):
    section_header("Bulk Entry", f"Out of {max_marks}")
    if not students:
        st.info("No students enrolled.")
        return
    rows = []
    for e in students:
        p   = e["profiles"]
        sid = p["id"]
        rows.append({"student_id":sid,"Name":_student_display_name(p),"Enrollment No":p.get("enrollment_number","—") or "—","Obtained":float(existing_marks.get(sid) or 0.0)})
    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df[["Name","Enrollment No","Obtained"]],
        column_config={
            "Name":          st.column_config.TextColumn(disabled=True),
            "Enrollment No": st.column_config.TextColumn(disabled=True),
            "Obtained":      st.column_config.NumberColumn(f"Marks (/{max_marks})", min_value=0.0, max_value=max_marks, step=0.5),
        },
        use_container_width=True, hide_index=True, key=f"editor_{key_prefix}",
    )
    if st.button("💾 Save All Marks", key=f"save_bulk_{key_prefix}", type="primary", use_container_width=True):
        saved = failed = 0
        for i, row in edited.iterrows():
            sid = df.iloc[i]["student_id"]
            if save_fn(sid, float(row["Obtained"])): saved += 1
            else: failed += 1
        if failed == 0: st.success(f"✅ Marks saved for {saved} student(s).")
        else: st.warning(f"⚠️ Saved: {saved}, Failed: {failed}")


def _render_individual_marks(students, existing_marks, max_marks, save_fn, key_prefix):
    section_header("Individual Entry", f"Out of {max_marks}")
    if not students:
        st.info("No students enrolled.")
        return
    for e in students:
        p       = e["profiles"]
        sid     = p["id"]
        name    = _student_display_name(p)
        current = existing_marks.get(sid)
        c1,c2,c3 = st.columns([4,2,1])
        c1.write(f"**{name}**  `{p.get('enrollment_number','') or ''}`")
        new_val = c2.number_input(f"/{max_marks}", min_value=0.0, max_value=max_marks,
            value=float(current) if current is not None else 0.0,
            step=0.5, label_visibility="collapsed", key=f"{key_prefix}_{sid}")
        if c3.button("💾", key=f"save_ind_{key_prefix}_{sid}", help="Save this mark"):
            if save_fn(sid, new_val): st.toast(f"✅ Saved: {name}", icon="✅")
            else: st.toast(f"❌ Failed: {name}", icon="❌")
        st.divider()


# ─────────────────────────────────────────────────────────────────
# GRADEBOOK SUMMARY
# ─────────────────────────────────────────────────────────────────

def render_gradebook_summary(course_uuid, students, can_submit=True, can_approve=False):
    scheme = GradingService.get_effective_scheme(course_uuid)
    section_header("Compile & Review Grades")
    if st.button("🔄 Compile All Grades", use_container_width=True, type="primary"):
        student_profiles = [{"id": e["profiles"]["id"]} for e in students]
        with st.spinner("Compiling grades..."):
            ok, msg = GradingService.compile_grades(course_uuid, student_profiles)
        if ok: st.success(f"✅ {msg}"); st.rerun()
        else:  st.error(f"❌ {msg}")

    compiled = GradingService.get_compiled_grades(course_uuid)
    if not compiled:
        st.info("No compiled grades yet. Click Compile to generate.")
        return

    st.divider()
    rows = []
    for g in compiled:
        p      = g.get("profiles", {}) or {}
        letter = g.get("letter_grade") or "—"
        total  = g.get("total_score")
        suggs  = suggest_grade_change(total, scheme) if total is not None else []
        rows.append({"Name":_student_display_name(p),"Enroll No":p.get("enrollment_number","—"),
                     "Quiz":f"{g.get('quiz_score','—')}","Assignment":f"{g.get('assignment_score','—')}",
                     "Midterm":f"{g.get('midterm_score','—')}","Final":f"{g.get('final_score','—')}",
                     "Total":f"{total:.2f}" if total is not None else "—",
                     "Grade":f"{_grade_colour(letter)} {letter}",
                     "Suggestions":" | ".join(suggs) if suggs else "—",
                     "Status":g.get("status","—").capitalize()})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    section_header("Grade Distribution")
    grade_counts: dict = {}
    for g in compiled:
        l = g.get("letter_grade") or "—"
        grade_counts[l] = grade_counts.get(l, 0) + 1
    st.bar_chart(pd.DataFrame([{"Grade":k,"Count":v} for k,v in sorted(grade_counts.items())]).set_index("Grade"))

    st.divider()
    statuses = {g["status"] for g in compiled}
    if can_submit and "draft" in statuses:
        if st.button("📤 Submit Grades for Approval", use_container_width=True, type="primary"):
            if GradingService.submit_grades(course_uuid): st.success("✅ Grades submitted."); st.rerun()
            else: st.error("❌ Submission failed.")
    if can_approve and "submitted" in statuses:
        c1,c2 = st.columns(2)
        if c1.button("✅ Approve Grades", use_container_width=True, type="primary"):
            if GradingService.approve_grades(course_uuid): st.success("✅ Approved."); st.rerun()
        if c2.button("📢 Approve & Release", use_container_width=True):
            if GradingService.approve_grades(course_uuid):
                GradingService.release_grades(course_uuid)
                st.success("✅ Approved and released."); st.rerun()
    if can_approve and "approved" in statuses:
        if st.button("📢 Release Grades to Students", use_container_width=True, type="primary"):
            if GradingService.release_grades(course_uuid): st.success("✅ Released."); st.rerun()
