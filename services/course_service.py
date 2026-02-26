import logging
import random
import string
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL

logger = logging.getLogger("sylemax.course_service")


def _generate_course_id() -> str:
    """Generates a random 7-char alphanumeric ID e.g. CS3X7K2."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(chars, k=7))


def _unique_course_id() -> str:
    """Generates a unique course_id not already in the courses table."""
    for _ in range(20):
        cid = _generate_course_id()
        resp = supabase.table("courses").select("id").eq("course_id", cid).execute()
        if not resp.data:
            return cid
    return _generate_course_id()  # fallback


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_all_courses(semester_id: str | None = None) -> list:
    try:
        query = (
            supabase
            .table("courses")
            .select("*, departments(name), semesters(name)")
            .order("code")
        )
        if semester_id:
            query = query.eq("semester_id", semester_id)
        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.exception("Failed to fetch courses.")
        return []


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_course(course_id: str) -> dict | None:
    try:
        response = (
            supabase
            .table("courses")
            .select("*, departments(name), semesters(name)")
            .eq("id", course_id)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.exception(f"Failed to fetch course: {course_id}")
        return None


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_faculty_courses(faculty_id: str, semester_id: str | None = None) -> list:
    try:
        query = (
            supabase
            .table("course_assignments")
            .select("*, courses(*, departments(name), semesters(name))")
            .eq("faculty_id", faculty_id)
        )
        response = query.execute()
        data = response.data or []
        if semester_id:
            data = [
                d for d in data
                if (d.get("courses") or {}).get("semester_id") == semester_id
            ]
        return data
    except Exception as e:
        logger.exception(f"Failed to fetch courses for faculty: {faculty_id}")
        return []


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_lookup_by_course_id(course_id_str: str) -> dict | None:
    """Look up a course by its short alphanumeric course_id (e.g. CS3X7K2)."""
    try:
        response = (
            supabase
            .table("courses")
            .select("*, departments(name), semesters(name)")
            .eq("course_id", course_id_str.strip().upper())
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.exception(f"Failed to lookup course_id: {course_id_str}")
        return None


class CourseService(BaseService):

    @staticmethod
    def get_all(semester_id: str | None = None) -> list:
        return _cached_get_all_courses(semester_id)

    @staticmethod
    def get_by_id(course_id: str) -> dict | None:
        return _cached_get_course(course_id)

    @staticmethod
    def get_faculty_courses(faculty_id: str, semester_id: str | None = None) -> list:
        return _cached_get_faculty_courses(faculty_id, semester_id)

    @staticmethod
    def lookup_by_course_id(course_id_str: str) -> dict | None:
        """Look up course by the 7-char alphanumeric course_id."""
        return _cached_lookup_by_course_id(course_id_str)

    @staticmethod
    def create(
        name: str,
        code: str,
        department_id: str,
        semester_id: str,
        credits: int,
        max_students: int,
        description: str = "",
        course_id_override: str = "",
    ) -> bool:
        try:
            course_id = course_id_override.strip().upper() if course_id_override.strip() \
                        else _unique_course_id()

            response = (
                supabase
                .table("courses")
                .insert({
                    "name":          name.strip(),
                    "code":          code.strip().upper(),
                    "course_id":     course_id,
                    "department_id": department_id,
                    "semester_id":   semester_id,
                    "credits":       credits,
                    "max_students":  max_students,
                    "description":   description.strip(),
                })
                .execute()
            )
            if response.data:
                CourseService.clear_cache()
                logger.info(f"Course created: {code} [{course_id}]")
                return True
            return False
        except Exception as e:
            logger.exception(f"Failed to create course: {name}")
            return False

    @staticmethod
    def update(course_id: str, updates: dict) -> bool:
        try:
            response = (
                supabase
                .table("courses")
                .update(updates)
                .eq("id", course_id)
                .execute()
            )
            if response.data:
                CourseService.clear_cache()
                return True
            return False
        except Exception as e:
            logger.exception(f"Failed to update course: {course_id}")
            return False

    @staticmethod
    def delete(course_id: str) -> bool:
        try:
            supabase.table("courses").delete().eq("id", course_id).execute()
            CourseService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Failed to delete course: {course_id}")
            return False

    @staticmethod
    def assign_faculty(course_id: str, faculty_id: str) -> bool:
        try:
            response = (
                supabase
                .table("course_assignments")
                .upsert({"course_id": course_id, "faculty_id": faculty_id})
                .execute()
            )
            if response.data:
                CourseService.clear_cache()
                return True
            return False
        except Exception as e:
            logger.exception(f"Failed to assign faculty to course: {course_id}")
            return False

    @staticmethod
    def unassign_faculty(course_id: str, faculty_id: str) -> bool:
        try:
            supabase.table("course_assignments")\
                .delete()\
                .eq("course_id", course_id)\
                .eq("faculty_id", faculty_id)\
                .execute()
            CourseService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Failed to unassign faculty from course: {course_id}")
            return False

    @staticmethod
    def get_assigned_faculty(course_id: str) -> list:
        try:
            response = (
                supabase
                .table("course_assignments")
                .select("*, profiles(id, email, first_name, last_name, full_name)")
                .eq("course_id", course_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.exception(f"Failed to fetch assigned faculty for course: {course_id}")
            return []

    @staticmethod
    def get_enrollment_count(course_id: str) -> int:
        try:
            response = (
                supabase
                .table("enrollments")
                .select("id", count="exact")
                .eq("course_id", course_id)
                .eq("status", "active")
                .execute()
            )
            return response.count or 0
        except Exception as e:
            logger.exception(f"Failed to get enrollment count: {course_id}")
            return 0
