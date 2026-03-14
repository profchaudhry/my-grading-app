"""
GradingService — core grading logic.
Handles scheme management, quiz/assignment/exam CRUD,
marks entry, compilation, and grade calculation.
"""
import logging
from typing import Optional
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL
from services.cache_utils import ttl_cache

logger = logging.getLogger("sylemax.grading_service")

GLOBAL_SCHEME_ID = "00000000-0000-0000-0000-000000000001"

DEFAULT_SCHEME = {
    "weight_quiz": 15, "weight_assignment": 20,
    "weight_midterm": 25, "weight_final": 40,
    "grade_a_min": 85,  "grade_a_m_min": 80,
    "grade_bp_min": 75, "grade_b_min": 71,
    "grade_b_m_min": 68,"grade_cp_min": 64,
    "grade_c_min": 60,  "grade_c_m_min": 57,
    "grade_dp_min": 53, "grade_d_min": 50,
}


# ── Scheme helpers ────────────────────────────────────────────────

def score_to_letter(score: float, scheme: dict) -> tuple[str, float]:
    """Returns (letter_grade, gpa_points) for a numeric score."""
    s = scheme
    thresholds = [
        (s["grade_a_min"],   "A",   4.0),
        (s["grade_a_m_min"], "A-",  3.7),
        (s["grade_bp_min"],  "B+",  3.3),
        (s["grade_b_min"],   "B",   3.0),
        (s["grade_b_m_min"], "B-",  2.7),
        (s["grade_cp_min"],  "C+",  2.3),
        (s["grade_c_min"],   "C",   2.0),
        (s["grade_c_m_min"], "C-",  1.7),
        (s["grade_dp_min"],  "D+",  1.3),
        (s["grade_d_min"],   "D",   1.0),
    ]
    for min_score, letter, gpa in thresholds:
        if score >= min_score:
            return letter, gpa
    return "F", 0.0


def suggest_grade_change(score: float, scheme: dict) -> list[str]:
    """Returns suggestions if +1 or +2 marks changes the letter grade."""
    current_letter, _ = score_to_letter(score, scheme)
    suggestions = []
    for delta in [1, 2]:
        new_letter, _ = score_to_letter(score + delta, scheme)
        if new_letter != current_letter:
            suggestions.append(
                f"+{delta} mark{'s' if delta > 1 else ''} → **{new_letter}** "
                f"(currently **{current_letter}**)"
            )
    return suggestions


@ttl_cache(ttl=CACHE_TTL)
def _cached_global_scheme() -> dict:
    try:
        r = supabase.table("grading_scheme").select("*")\
            .eq("id", GLOBAL_SCHEME_ID).execute()
        return r.data[0] if r.data else DEFAULT_SCHEME.copy()
    except Exception as e:
        logger.exception("Failed to fetch global scheme.")
        return DEFAULT_SCHEME.copy()


@ttl_cache(ttl=CACHE_TTL)
def _cached_course_scheme(course_uuid: str) -> dict | None:
    try:
        r = supabase.table("course_grading_scheme").select("*")\
            .eq("course_id", course_uuid).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.exception(f"Failed to fetch course scheme: {course_uuid}")
        return None


class GradingService(BaseService):

    # ── Scheme ───────────────────────────────────────────────────

    @staticmethod
    def get_global_scheme() -> dict:
        return _cached_global_scheme()

    @staticmethod
    def get_effective_scheme(course_uuid: str) -> dict:
        """Returns course override if set, otherwise global scheme."""
        override = _cached_course_scheme(course_uuid)
        return override if override else _cached_global_scheme()

    @staticmethod
    def update_global_scheme(data: dict) -> bool:
        try:
            r = supabase.table("grading_scheme").update(data)\
                .eq("id", GLOBAL_SCHEME_ID).execute()
            GradingService.clear_cache()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to update global scheme.")
            return False

    @staticmethod
    def save_course_scheme(course_uuid: str, data: dict) -> bool:
        try:
            data["course_id"] = course_uuid
            r = supabase.table("course_grading_scheme").upsert(data, on_conflict="course_id").execute()
            GradingService.clear_cache()
            return bool(r.data)
        except Exception as e:
            logger.exception(f"Failed to save course scheme: {course_uuid}")
            return False

    @staticmethod
    def reset_course_scheme(course_uuid: str) -> bool:
        """Delete course override so it falls back to global scheme."""
        try:
            supabase.table("course_grading_scheme")\
                .delete().eq("course_id", course_uuid).execute()
            GradingService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Failed to reset course scheme: {course_uuid}")
            return False

    # ── Quizzes ───────────────────────────────────────────────────

    @staticmethod
    def get_quizzes(course_uuid: str) -> list:
        try:
            r = supabase.table("quizzes").select("*")\
                .eq("course_id", course_uuid).order("order_no").execute()
            return r.data or []
        except Exception as e:
            logger.exception(f"Failed to fetch quizzes: {course_uuid}")
            return []

    @staticmethod
    def add_quiz(course_uuid: str, title: str, total_marks: float,
                 weight: float | None, clo_no: str, order_no: int) -> bool:
        try:
            r = supabase.table("quizzes").insert({
                "course_id": course_uuid, "title": title,
                "total_marks": total_marks, "weight": weight,
                "clo_no": clo_no, "order_no": order_no,
            }).execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to add quiz.")
            return False

    @staticmethod
    def update_quiz(quiz_id: str, data: dict) -> bool:
        try:
            r = supabase.table("quizzes").update(data).eq("id", quiz_id).execute()
            return bool(r.data)
        except Exception as e:
            logger.exception(f"Failed to update quiz: {quiz_id}")
            return False

    @staticmethod
    def delete_quiz(quiz_id: str) -> bool:
        try:
            supabase.table("quizzes").delete().eq("id", quiz_id).execute()
            return True
        except Exception as e:
            logger.exception(f"Failed to delete quiz: {quiz_id}")
            return False

    @staticmethod
    def get_quiz_config(course_uuid: str) -> dict:
        try:
            r = supabase.table("quiz_config").select("*")\
                .eq("course_id", course_uuid).execute()
            return r.data[0] if r.data else {"method": "equal", "best_of_n": None, "compiled": False}
        except Exception:
            return {"method": "equal", "best_of_n": None, "compiled": False}

    @staticmethod
    def save_quiz_config(course_uuid: str, method: str, best_of_n: int | None) -> bool:
        try:
            r = supabase.table("quiz_config").upsert({
                "course_id": course_uuid, "method": method,
                "best_of_n": best_of_n, "compiled": False,
            }, on_conflict="course_id").execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to save quiz config.")
            return False

    # ── Assignments ───────────────────────────────────────────────

    @staticmethod
    def get_assignments(course_uuid: str) -> list:
        try:
            r = supabase.table("assignments").select("*")\
                .eq("course_id", course_uuid).order("order_no").execute()
            return r.data or []
        except Exception as e:
            logger.exception(f"Failed to fetch assignments: {course_uuid}")
            return []

    @staticmethod
    def add_assignment(course_uuid: str, title: str, total_marks: float,
                       weight: float | None, clo_no: str, order_no: int) -> bool:
        try:
            r = supabase.table("assignments").insert({
                "course_id": course_uuid, "title": title,
                "total_marks": total_marks, "weight": weight,
                "clo_no": clo_no, "order_no": order_no,
            }).execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to add assignment.")
            return False

    @staticmethod
    def update_assignment(assignment_id: str, data: dict) -> bool:
        try:
            r = supabase.table("assignments").update(data)\
                .eq("id", assignment_id).execute()
            return bool(r.data)
        except Exception as e:
            logger.exception(f"Failed to update assignment: {assignment_id}")
            return False

    @staticmethod
    def delete_assignment(assignment_id: str) -> bool:
        try:
            supabase.table("assignments").delete().eq("id", assignment_id).execute()
            return True
        except Exception as e:
            logger.exception(f"Failed to delete assignment: {assignment_id}")
            return False

    @staticmethod
    def get_assignment_config(course_uuid: str) -> dict:
        try:
            r = supabase.table("assignment_config").select("*")\
                .eq("course_id", course_uuid).execute()
            return r.data[0] if r.data else {"method": "equal", "best_of_n": None, "compiled": False}
        except Exception:
            return {"method": "equal", "best_of_n": None, "compiled": False}

    @staticmethod
    def save_assignment_config(course_uuid: str, method: str, best_of_n: int | None) -> bool:
        try:
            r = supabase.table("assignment_config").upsert({
                "course_id": course_uuid, "method": method,
                "best_of_n": best_of_n, "compiled": False,
            }, on_conflict="course_id").execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to save assignment config.")
            return False

    # ── Midterm ───────────────────────────────────────────────────

    @staticmethod
    def get_midterm(course_uuid: str) -> dict | None:
        try:
            r = supabase.table("midterm_exams").select("*")\
                .eq("course_id", course_uuid).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.exception(f"Failed to fetch midterm: {course_uuid}")
            return None

    @staticmethod
    def create_midterm(course_uuid: str, entry_mode: str, total_marks: float) -> dict | None:
        try:
            r = supabase.table("midterm_exams").upsert({
                "course_id": course_uuid,
                "entry_mode": entry_mode,
                "total_marks": total_marks,
            }, on_conflict="course_id").execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.exception("Failed to create midterm.")
            return None

    @staticmethod
    def get_midterm_questions(midterm_id: str) -> list:
        try:
            r = supabase.table("midterm_questions").select("*")\
                .eq("midterm_id", midterm_id).order("order_no").execute()
            return r.data or []
        except Exception:
            return []

    @staticmethod
    def add_midterm_question(midterm_id: str, q_no: int, clo_no: str,
                              total_marks: float, order_no: int) -> bool:
        try:
            r = supabase.table("midterm_questions").insert({
                "midterm_id": midterm_id, "question_no": q_no,
                "clo_no": clo_no, "total_marks": total_marks, "order_no": order_no,
            }).execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to add midterm question.")
            return False

    @staticmethod
    def delete_midterm_question(q_id: str) -> bool:
        try:
            supabase.table("midterm_questions").delete().eq("id", q_id).execute()
            return True
        except Exception as e:
            return False

    # ── Final exam ────────────────────────────────────────────────

    @staticmethod
    def get_final(course_uuid: str) -> dict | None:
        try:
            r = supabase.table("final_exams").select("*")\
                .eq("course_id", course_uuid).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.exception(f"Failed to fetch final: {course_uuid}")
            return None

    @staticmethod
    def create_final(course_uuid: str, entry_mode: str, total_marks: float) -> dict | None:
        try:
            r = supabase.table("final_exams").upsert({
                "course_id": course_uuid,
                "entry_mode": entry_mode,
                "total_marks": total_marks,
            }, on_conflict="course_id").execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.exception("Failed to create final exam.")
            return None

    @staticmethod
    def get_final_questions(final_id: str) -> list:
        try:
            r = supabase.table("final_questions").select("*")\
                .eq("final_id", final_id).order("order_no").execute()
            return r.data or []
        except Exception:
            return []

    @staticmethod
    def add_final_question(final_id: str, q_no: int, clo_no: str,
                            total_marks: float, order_no: int) -> bool:
        try:
            r = supabase.table("final_questions").insert({
                "final_id": final_id, "question_no": q_no,
                "clo_no": clo_no, "total_marks": total_marks, "order_no": order_no,
            }).execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to add final question.")
            return False

    @staticmethod
    def delete_final_question(q_id: str) -> bool:
        try:
            supabase.table("final_questions").delete().eq("id", q_id).execute()
            return True
        except Exception:
            return False

    # ── Marks entry ───────────────────────────────────────────────

    @staticmethod
    def get_quiz_marks(quiz_id: str) -> list:
        try:
            r = supabase.table("quiz_marks")\
                .select("*, profiles(id, full_name, first_name, last_name, enrollment_number)")\
                .eq("quiz_id", quiz_id).execute()
            return r.data or []
        except Exception:
            return []

    @staticmethod
    def save_quiz_mark(quiz_id: str, student_id: str, obtained: float | None) -> bool:
        try:
            r = supabase.table("quiz_marks").upsert({
                "quiz_id": quiz_id, "student_id": student_id, "obtained": obtained,
            }, on_conflict="quiz_id,student_id").execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to save quiz mark.")
            return False

    @staticmethod
    def get_assignment_marks(assignment_id: str) -> list:
        try:
            r = supabase.table("assignment_marks")\
                .select("*, profiles(id, full_name, first_name, last_name, enrollment_number)")\
                .eq("assignment_id", assignment_id).execute()
            return r.data or []
        except Exception:
            return []

    @staticmethod
    def save_assignment_mark(assignment_id: str, student_id: str, obtained: float | None) -> bool:
        try:
            r = supabase.table("assignment_marks").upsert({
                "assignment_id": assignment_id, "student_id": student_id, "obtained": obtained,
            }, on_conflict="assignment_id,student_id").execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to save assignment mark.")
            return False

    @staticmethod
    def get_midterm_marks(midterm_id: str) -> list:
        try:
            r = supabase.table("midterm_marks")\
                .select("*, profiles(id, full_name, first_name, last_name, enrollment_number)")\
                .eq("midterm_id", midterm_id).execute()
            return r.data or []
        except Exception:
            return []

    @staticmethod
    def save_midterm_mark(midterm_id: str, student_id: str, obtained: float | None) -> bool:
        try:
            r = supabase.table("midterm_marks").upsert({
                "midterm_id": midterm_id, "student_id": student_id,
                "total_obtained": obtained,
            }, on_conflict="midterm_id,student_id").execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to save midterm mark.")
            return False

    @staticmethod
    def get_midterm_question_marks(midterm_id: str, student_id: str) -> list:
        try:
            r = supabase.table("midterm_question_marks").select("*")\
                .eq("midterm_id", midterm_id).eq("student_id", student_id).execute()
            return r.data or []
        except Exception:
            return []

    @staticmethod
    def save_midterm_question_mark(midterm_id: str, question_id: str,
                                    student_id: str, obtained: float | None) -> bool:
        try:
            r = supabase.table("midterm_question_marks").upsert({
                "midterm_id": midterm_id, "question_id": question_id,
                "student_id": student_id, "obtained": obtained,
            }, on_conflict="question_id,student_id").execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to save midterm question mark.")
            return False

    @staticmethod
    def get_final_marks(final_id: str) -> list:
        try:
            r = supabase.table("final_marks")\
                .select("*, profiles(id, full_name, first_name, last_name, enrollment_number)")\
                .eq("final_id", final_id).execute()
            return r.data or []
        except Exception:
            return []

    @staticmethod
    def save_final_mark(final_id: str, student_id: str, obtained: float | None) -> bool:
        try:
            r = supabase.table("final_marks").upsert({
                "final_id": final_id, "student_id": student_id,
                "total_obtained": obtained,
            }, on_conflict="final_id,student_id").execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to save final mark.")
            return False

    @staticmethod
    def get_final_question_marks(final_id: str, student_id: str) -> list:
        try:
            r = supabase.table("final_question_marks").select("*")\
                .eq("final_id", final_id).eq("student_id", student_id).execute()
            return r.data or []
        except Exception:
            return []

    @staticmethod
    def save_final_question_mark(final_id: str, question_id: str,
                                  student_id: str, obtained: float | None) -> bool:
        try:
            r = supabase.table("final_question_marks").upsert({
                "final_id": final_id, "question_id": question_id,
                "student_id": student_id, "obtained": obtained,
            }, on_conflict="question_id,student_id").execute()
            return bool(r.data)
        except Exception as e:
            logger.exception("Failed to save final question mark.")
            return False

    # ── Compilation ───────────────────────────────────────────────

    @staticmethod
    def compile_grades(course_uuid: str, students: list) -> tuple[bool, str]:
        """
        Computes final compiled_grades for all students in a course.
        Returns (success, message).
        """
        try:
            scheme    = GradingService.get_effective_scheme(course_uuid)
            w_quiz    = float(scheme["weight_quiz"])
            w_asgn    = float(scheme["weight_assignment"])
            w_mid     = float(scheme["weight_midterm"])
            w_fin     = float(scheme["weight_final"])

            quizzes   = GradingService.get_quizzes(course_uuid)
            quiz_cfg  = GradingService.get_quiz_config(course_uuid)
            asgns     = GradingService.get_assignments(course_uuid)
            asgn_cfg  = GradingService.get_assignment_config(course_uuid)
            midterm   = GradingService.get_midterm(course_uuid)
            final     = GradingService.get_final(course_uuid)

            rows_to_upsert = []

            for student in students:
                sid = student["id"]

                # ── Quiz score ─────────────────────────────────
                quiz_score_out_of_w = None
                if quizzes:
                    raw_scores = []
                    for q in quizzes:
                        marks = supabase.table("quiz_marks").select("obtained")\
                            .eq("quiz_id", q["id"]).eq("student_id", sid).execute()
                        val = marks.data[0]["obtained"] if marks.data and \
                              marks.data[0]["obtained"] is not None else None
                        raw_scores.append((q, val))

                    method   = quiz_cfg.get("method", "equal")
                    best_of_n = quiz_cfg.get("best_of_n")

                    if method == "best_of" and best_of_n:
                        scored = sorted(
                            [v for _, v in raw_scores if v is not None],
                            reverse=True
                        )[:best_of_n]
                        totals = sorted(
                            [float(q["total_marks"]) for q, v in raw_scores if v is not None],
                            reverse=True
                        )[:best_of_n]
                        raw_total = sum(scored)
                        max_total = sum(totals) or 1
                    elif method == "weighted":
                        raw_total = sum(
                            float(v) * float(q.get("weight") or 1)
                            for q, v in raw_scores if v is not None
                        )
                        max_total = sum(
                            float(q["total_marks"]) * float(q.get("weight") or 1)
                            for q in quizzes
                        ) or 1
                    else:  # equal
                        raw_total = sum(float(v) for _, v in raw_scores if v is not None)
                        max_total = sum(float(q["total_marks"]) for q in quizzes) or 1

                    quiz_score_out_of_w = round((raw_total / max_total) * w_quiz, 2)

                # ── Assignment score ───────────────────────────
                asgn_score_out_of_w = None
                if asgns:
                    raw_scores = []
                    for a in asgns:
                        marks = supabase.table("assignment_marks").select("obtained")\
                            .eq("assignment_id", a["id"]).eq("student_id", sid).execute()
                        val = marks.data[0]["obtained"] if marks.data and \
                              marks.data[0]["obtained"] is not None else None
                        raw_scores.append((a, val))

                    method    = asgn_cfg.get("method", "equal")
                    best_of_n = asgn_cfg.get("best_of_n")

                    if method == "best_of" and best_of_n:
                        scored = sorted(
                            [v for _, v in raw_scores if v is not None],
                            reverse=True
                        )[:best_of_n]
                        totals = sorted(
                            [float(a["total_marks"]) for a, v in raw_scores if v is not None],
                            reverse=True
                        )[:best_of_n]
                        raw_total = sum(scored)
                        max_total = sum(totals) or 1
                    elif method == "weighted":
                        raw_total = sum(
                            float(v) * float(a.get("weight") or 1)
                            for a, v in raw_scores if v is not None
                        )
                        max_total = sum(
                            float(a["total_marks"]) * float(a.get("weight") or 1)
                            for a in asgns
                        ) or 1
                    else:
                        raw_total = sum(float(v) for _, v in raw_scores if v is not None)
                        max_total = sum(float(a["total_marks"]) for a in asgns) or 1

                    asgn_score_out_of_w = round((raw_total / max_total) * w_asgn, 2)

                # ── Midterm score ──────────────────────────────
                mid_score_out_of_w = None
                if midterm:
                    mid_id = midterm["id"]
                    if midterm["entry_mode"] == "total":
                        r = supabase.table("midterm_marks").select("total_obtained")\
                            .eq("midterm_id", mid_id).eq("student_id", sid).execute()
                        if r.data and r.data[0]["total_obtained"] is not None:
                            mid_score_out_of_w = round(
                                (float(r.data[0]["total_obtained"]) /
                                 float(midterm["total_marks"])) * w_mid, 2
                            )
                    else:
                        questions = GradingService.get_midterm_questions(mid_id)
                        obtained  = 0.0
                        max_m     = 0.0
                        for q in questions:
                            qr = supabase.table("midterm_question_marks").select("obtained")\
                                .eq("question_id", q["id"]).eq("student_id", sid).execute()
                            if qr.data and qr.data[0]["obtained"] is not None:
                                obtained += float(qr.data[0]["obtained"])
                            max_m += float(q["total_marks"])
                        if max_m > 0:
                            mid_score_out_of_w = round((obtained / max_m) * w_mid, 2)

                # ── Final score ────────────────────────────────
                fin_score_out_of_w = None
                if final:
                    fin_id = final["id"]
                    if final["entry_mode"] == "total":
                        r = supabase.table("final_marks").select("total_obtained")\
                            .eq("final_id", fin_id).eq("student_id", sid).execute()
                        if r.data and r.data[0]["total_obtained"] is not None:
                            fin_score_out_of_w = round(
                                (float(r.data[0]["total_obtained"]) /
                                 float(final["total_marks"])) * w_fin, 2
                            )
                    else:
                        questions = GradingService.get_final_questions(fin_id)
                        obtained  = 0.0
                        max_f     = 0.0
                        for q in questions:
                            qr = supabase.table("final_question_marks").select("obtained")\
                                .eq("question_id", q["id"]).eq("student_id", sid).execute()
                            if qr.data and qr.data[0]["obtained"] is not None:
                                obtained += float(qr.data[0]["obtained"])
                            max_f += float(q["total_marks"])
                        if max_f > 0:
                            fin_score_out_of_w = round((obtained / max_f) * w_fin, 2)

                # ── Total ──────────────────────────────────────
                parts = [s for s in [quiz_score_out_of_w, asgn_score_out_of_w,
                                     mid_score_out_of_w, fin_score_out_of_w]
                         if s is not None]
                total = round(sum(parts), 2) if parts else None

                letter, gpa = score_to_letter(total, scheme) if total is not None \
                              else (None, None)

                rows_to_upsert.append({
                    "course_id":         course_uuid,
                    "student_id":        sid,
                    "quiz_score":        quiz_score_out_of_w,
                    "assignment_score":  asgn_score_out_of_w,
                    "midterm_score":     mid_score_out_of_w,
                    "final_score":       fin_score_out_of_w,
                    "total_score":       total,
                    "letter_grade":      letter,
                    "gpa_points":        gpa,
                    "status":            "draft",
                })

            # Batch upsert — on_conflict targets the unique key so existing rows are updated
            supabase.table("compiled_grades").upsert(
                rows_to_upsert,
                on_conflict="course_id,student_id"
            ).execute()

            # Mark quiz/assignment configs as compiled
            supabase.table("quiz_config").upsert(
                {"course_id": course_uuid, "compiled": True},
                on_conflict="course_id"
            ).execute()
            supabase.table("assignment_config").upsert(
                {"course_id": course_uuid, "compiled": True},
                on_conflict="course_id"
            ).execute()

            GradingService.clear_cache()
            return True, f"Grades compiled for {len(rows_to_upsert)} student(s)."

        except Exception as e:
            logger.exception(f"Compile failed for course {course_uuid}")
            return False, str(e)

    @staticmethod
    def submit_grades(course_uuid: str) -> bool:
        """Faculty submits compiled grades for admin approval."""
        try:
            from datetime import datetime, timezone
            supabase.table("compiled_grades").update({
                "status": "submitted",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }).eq("course_id", course_uuid).eq("status", "draft").execute()
            GradingService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Submit failed for course {course_uuid}")
            return False

    @staticmethod
    def approve_grades(course_uuid: str) -> bool:
        """Admin approves submitted grades."""
        try:
            from datetime import datetime, timezone
            supabase.table("compiled_grades").update({
                "status": "approved",
                "approved_at": datetime.now(timezone.utc).isoformat(),
            }).eq("course_id", course_uuid).eq("status", "submitted").execute()
            GradingService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Approve failed for course {course_uuid}")
            return False

    @staticmethod
    def release_grades(course_uuid: str) -> bool:
        """Admin releases approved grades for students to view."""
        try:
            from datetime import datetime, timezone
            supabase.table("compiled_grades").update({
                "status": "released",
                "released_at": datetime.now(timezone.utc).isoformat(),
            }).eq("course_id", course_uuid).eq("status", "approved").execute()
            GradingService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Release failed for course {course_uuid}")
            return False

    @staticmethod
    def get_compiled_grades(course_uuid: str) -> list:
        try:
            r = supabase.table("compiled_grades")\
                .select("*, profiles(id, full_name, first_name, last_name, enrollment_number, program)")\
                .eq("course_id", course_uuid)\
                .order("total_score", desc=True)\
                .execute()
            return r.data or []
        except Exception as e:
            logger.exception(f"Failed to fetch compiled grades: {course_uuid}")
            return []

    @staticmethod
    def get_student_grades(student_id: str) -> list:
        """Fetch released grades for a student across all courses."""
        try:
            r = supabase.table("compiled_grades")\
                .select("*, courses(name, code, course_id, credits)")\
                .eq("student_id", student_id)\
                .eq("status", "released")\
                .execute()
            return r.data or []
        except Exception as e:
            logger.exception(f"Failed to fetch student grades: {student_id}")
            return []
