import logging
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL
from services.cache_utils import ttl_cache

logger = logging.getLogger("sylemax.enrollment_service")


@ttl_cache(ttl=CACHE_TTL)
def _cached_get_course_enrollments(course_id: str) -> list:
    try:
        response = (
            supabase
            .table("enrollments")
            .select("*, profiles(id, email, first_name, last_name, student_id, enrollment_number, program, year_of_study, phone)")
            .eq("course_id", course_id)
            .eq("status", "active")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception(f"Failed to fetch enrollments for course {course_id}")
        return []


@ttl_cache(ttl=CACHE_TTL)
def _cached_get_student_enrollments(student_id: str) -> list:
    try:
        response = (
            supabase
            .table("enrollments")
            .select("*, courses(id, name, code, credits, departments(name)), semesters(name)")
            .eq("student_id", student_id)
            .eq("status", "active")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception(f"Failed to fetch enrollments for student {student_id}")
        return []


class EnrollmentService(BaseService):

    @staticmethod
    def get_course_enrollments(course_id: str) -> list:
        return _cached_get_course_enrollments(course_id)

    @staticmethod
    def get_student_enrollments(student_id: str) -> list:
        return _cached_get_student_enrollments(student_id)

    @staticmethod
    def enroll_student(student_id: str, course_id: str, semester_id: str) -> bool:
        try:
            response = (
                supabase
                .table("enrollments")
                .upsert({
                    "student_id":  student_id,
                    "course_id":   course_id,
                    "semester_id": semester_id,
                    "status":      "active",
                })
                .execute()
            )
            if response.data:
                EnrollmentService.clear_cache()
                return True
            return False
        except Exception as e:
            logger.exception(f"Failed to enroll student {student_id} in course {course_id}")
            return False

    @staticmethod
    def drop_student(student_id: str, course_id: str, semester_id: str) -> bool:
        try:
            supabase.table("enrollments")\
                .update({"status": "dropped"})\
                .eq("student_id", student_id)\
                .eq("course_id", course_id)\
                .eq("semester_id", semester_id)\
                .execute()
            EnrollmentService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Failed to drop student {student_id} from course {course_id}")
            return False

    @staticmethod
    def bulk_enroll(enrollments: list[dict]) -> tuple[int, int]:
        """
        Bulk enroll a list of dicts with keys: student_id, course_id, semester_id.
        Returns (success_count, fail_count).
        """
        success, fail = 0, 0
        for e in enrollments:
            if EnrollmentService.enroll_student(
                e["student_id"], e["course_id"], e["semester_id"]
            ):
                success += 1
            else:
                fail += 1
        if success:
            EnrollmentService.clear_cache()
        return success, fail
