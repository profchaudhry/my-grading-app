"""
ReportsService — aggregated analytics queries for Phase 5.
"""
import logging
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL

logger = logging.getLogger("sylemax.reports_service")


class ReportsService(BaseService):

    # ── Course performance ────────────────────────────────────────
    @staticmethod
    def course_grade_distribution(course_uuid: str) -> dict:
        """Grade distribution + pass/fail for a course."""
        try:
            r = supabase.table("compiled_grades")\
                .select("letter_grade, total_score, status")\
                .eq("course_id", course_uuid)\
                .execute()
            rows = r.data or []
            dist, total, passed, failed = {}, 0, 0, 0
            scores = []
            for row in rows:
                lg = row.get("letter_grade") or "—"
                dist[lg] = dist.get(lg, 0) + 1
                total += 1
                ts = row.get("total_score")
                if ts is not None:
                    scores.append(float(ts))
                    if lg != "F":
                        passed += 1
                    else:
                        failed += 1
            return {
                "distribution": dist,
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": round(passed / total * 100, 1) if total else 0,
                "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
                "highest": max(scores) if scores else 0,
                "lowest": min(scores) if scores else 0,
            }
        except Exception as e:
            logger.exception(f"course_grade_distribution failed: {course_uuid}")
            return {}

    # ── Enrollment analytics ──────────────────────────────────────
    @staticmethod
    def enrollment_by_semester(semester_id: str | None = None) -> list:
        try:
            q = supabase.table("enrollments")\
                .select("course_id, courses(name, code, course_id, max_students, semester_id, semesters(name))")\
                .eq("status", "active")
            if semester_id:
                q = q.eq("courses.semester_id", semester_id)
            r = q.execute()
            rows = r.data or []
            counts: dict[str, dict] = {}
            for row in rows:
                cid = row.get("course_id")
                if not cid:
                    continue
                if cid not in counts:
                    c = row.get("courses") or {}
                    counts[cid] = {
                        "course_id":   c.get("course_id","—"),
                        "code":        c.get("code","—"),
                        "name":        c.get("name","—"),
                        "max_students":c.get("max_students", 0),
                        "semester":    (c.get("semesters") or {}).get("name","—"),
                        "enrolled":    0,
                    }
                counts[cid]["enrolled"] += 1
            result = sorted(counts.values(), key=lambda x: x["enrolled"], reverse=True)
            for r in result:
                mx = r["max_students"] or 1
                r["fill_rate"] = round(r["enrolled"] / mx * 100, 1)
            return result
        except Exception as e:
            logger.exception("enrollment_by_semester failed")
            return []

    # ── Faculty workload ──────────────────────────────────────────
    @staticmethod
    def faculty_workload(semester_id: str | None = None) -> list:
        try:
            q = supabase.table("course_assignments")\
                .select("faculty_id, profiles(id, first_name, last_name, full_name, email), courses(id, name, code, semester_id, max_students)")
            r = q.execute()
            rows = r.data or []
            faculty: dict[str, dict] = {}
            for row in rows:
                fid = row.get("faculty_id")
                course = row.get("courses") or {}
                if semester_id and course.get("semester_id") != semester_id:
                    continue
                if not fid:
                    continue
                if fid not in faculty:
                    p = row.get("profiles") or {}
                    fn = (p.get("full_name") or
                          f"{p.get('first_name','')} {p.get('last_name','')}").strip()
                    faculty[fid] = {
                        "faculty_id":   fid,
                        "name":         fn or p.get("email","—"),
                        "email":        p.get("email","—"),
                        "courses":      [],
                        "total_students": 0,
                    }
                faculty[fid]["courses"].append(
                    f"{course.get('code','—')} — {course.get('name','—')}"
                )
                # count enrolled students
                try:
                    ec = supabase.table("enrollments")\
                        .select("id", count="exact")\
                        .eq("course_id", course.get("id",""))\
                        .eq("status","active").execute()
                    faculty[fid]["total_students"] += (ec.count or 0)
                except Exception:
                    pass
            result = sorted(faculty.values(),
                             key=lambda x: len(x["courses"]), reverse=True)
            for f in result:
                f["num_courses"] = len(f["courses"])
            return result
        except Exception as e:
            logger.exception("faculty_workload failed")
            return []

    # ── Gradebook completion ──────────────────────────────────────
    @staticmethod
    def gradebook_completion(semester_id: str | None = None) -> list:
        try:
            q = supabase.table("courses")\
                .select("id, name, code, course_id, semester_id, semesters(name)")
            if semester_id:
                q = q.eq("semester_id", semester_id)
            r = q.execute()
            courses = r.data or []
            result = []
            for c in courses:
                cid = c["id"]
                # Count enrolled
                ec = supabase.table("enrollments")\
                    .select("id", count="exact")\
                    .eq("course_id", cid).eq("status","active").execute()
                enrolled = ec.count or 0
                # Get grade statuses
                gc = supabase.table("compiled_grades")\
                    .select("status").eq("course_id", cid).execute()
                grade_rows = gc.data or []
                statuses = {g["status"] for g in grade_rows}
                if "released" in statuses:
                    completion = "released"
                elif "approved" in statuses:
                    completion = "approved"
                elif "submitted" in statuses:
                    completion = "submitted"
                elif grade_rows:
                    completion = "draft"
                else:
                    completion = "not_started"
                result.append({
                    "code":       c.get("code","—"),
                    "name":       c.get("name","—"),
                    "course_id":  c.get("course_id","—"),
                    "semester":   (c.get("semesters") or {}).get("name","—"),
                    "enrolled":   enrolled,
                    "graded":     len(grade_rows),
                    "status":     completion,
                })
            return sorted(result, key=lambda x: x["status"])
        except Exception as e:
            logger.exception("gradebook_completion failed")
            return []

    # ── Comparative semester analytics ───────────────────────────
    @staticmethod
    def semester_comparison() -> list:
        try:
            r = supabase.table("semesters").select("id, name").execute()
            sems = r.data or []
            result = []
            for sem in sems:
                sid = sem["id"]
                # courses this semester
                cc = supabase.table("courses")\
                    .select("id", count="exact")\
                    .eq("semester_id", sid).execute()
                n_courses = cc.count or 0
                # enrollments
                course_ids_r = supabase.table("courses")\
                    .select("id").eq("semester_id", sid).execute()
                course_ids = [c["id"] for c in (course_ids_r.data or [])]
                n_students = 0
                avg_score = None
                pass_rate = None
                if course_ids:
                    ec = supabase.table("enrollments")\
                        .select("id", count="exact")\
                        .in_("course_id", course_ids)\
                        .eq("status","active").execute()
                    n_students = ec.count or 0
                    gr = supabase.table("compiled_grades")\
                        .select("total_score, letter_grade")\
                        .in_("course_id", course_ids).execute()
                    grades = gr.data or []
                    if grades:
                        scores = [float(g["total_score"]) for g in grades
                                  if g.get("total_score") is not None]
                        avg_score = round(sum(scores)/len(scores),2) if scores else None
                        passed = sum(1 for g in grades
                                     if g.get("letter_grade") not in (None,"F","—"))
                        pass_rate = round(passed/len(grades)*100,1)
                result.append({
                    "semester":   sem["name"],
                    "courses":    n_courses,
                    "students":   n_students,
                    "avg_score":  avg_score,
                    "pass_rate":  pass_rate,
                })
            return result
        except Exception as e:
            logger.exception("semester_comparison failed")
            return []

    # ── Student transcript ────────────────────────────────────────
    @staticmethod
    def student_transcript(student_id: str) -> dict:
        try:
            # Profile
            pr = supabase.table("profiles").select("*")\
                .eq("id", student_id).execute()
            profile = pr.data[0] if pr.data else {}
            # Grades
            gr = supabase.table("compiled_grades")\
                .select("*, courses(name, code, course_id, credits, semester_id, semesters(name))")\
                .eq("student_id", student_id)\
                .in_("status", ["approved","released"])\
                .execute()
            grades = gr.data or []
            # GPA calc
            total_credits = 0
            total_quality = 0.0
            semester_map: dict[str, list] = {}
            for g in grades:
                c = g.get("courses") or {}
                sem_name = (c.get("semesters") or {}).get("name","—")
                credits = float(c.get("credits") or 3)
                gpa_pts = float(g.get("gpa_points") or 0)
                total_credits += credits
                total_quality += gpa_pts * credits
                if sem_name not in semester_map:
                    semester_map[sem_name] = []
                semester_map[sem_name].append({
                    "code":         c.get("code","—"),
                    "name":         c.get("name","—"),
                    "credits":      credits,
                    "total_score":  g.get("total_score"),
                    "letter_grade": g.get("letter_grade","—"),
                    "gpa_points":   gpa_pts,
                    "status":       g.get("status","—"),
                })
            cgpa = round(total_quality / total_credits, 2) if total_credits else None
            return {
                "profile":        profile,
                "grades":         grades,
                "semester_map":   semester_map,
                "total_credits":  total_credits,
                "cgpa":           cgpa,
            }
        except Exception as e:
            logger.exception(f"student_transcript failed: {student_id}")
            return {}

    # ── Admin summary dashboard counts ───────────────────────────
    @staticmethod
    def admin_summary() -> dict:
        try:
            def count(table, filters=None):
                q = supabase.table(table).select("id", count="exact")
                if filters:
                    for k, v in filters.items():
                        q = q.eq(k, v)
                return q.execute().count or 0

            return {
                "total_students": count("profiles", {"role": "student"}),
                "total_faculty":  count("profiles", {"role": "faculty"}) +
                                  count("profiles", {"role": "faculty_ultra"}),
                "total_courses":  count("courses"),
                "total_enrolled": count("enrollments", {"status": "active"}),
                "pending_grades": count("compiled_grades", {"status": "submitted"}),
                "released_grades":count("compiled_grades", {"status": "released"}),
            }
        except Exception as e:
            logger.exception("admin_summary failed")
            return {}
