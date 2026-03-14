import logging
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL
from services.cache_utils import ttl_cache

logger = logging.getLogger("sylemax.faculty_service")


@ttl_cache(ttl=CACHE_TTL)
def _cached_get_faculty_profile(user_id: str) -> dict | None:
    try:
        response = (
            supabase
            .table("profiles")
            .select("*")
            .eq("id", user_id)
            .execute()
        )
        data = response.data
        return data[0] if data else None
    except Exception as e:
        logger.exception(f"Failed to fetch faculty profile for user_id={user_id}")
        return None


@ttl_cache(ttl=CACHE_TTL)
def _cached_get_assigned_courses(user_id: str) -> list:
    try:
        response = (
            supabase
            .table("course_assignments")
            .select("*, courses(*)")
            .eq("faculty_id", user_id)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception(f"Failed to fetch courses for faculty user_id={user_id}")
        return []


class FacultyService(BaseService):

    @staticmethod
    def get_profile(user_id: str) -> dict | None:
        return _cached_get_faculty_profile(user_id)

    @staticmethod
    def get_assigned_courses(user_id: str) -> list:
        return _cached_get_assigned_courses(user_id)

    @staticmethod
    def ensure_profile_exists(user, role: str = "faculty") -> dict | None:
        """
        Creates a faculty profile pending admin approval.
        Returns the profile dict, or None if creation failed.
        """
        existing = FacultyService.get_profile(user.id)
        if existing:
            return existing

        try:
            insert_response = supabase.table("profiles").insert({
                "id": user.id,
                "email": user.email,
                "role": role,
                "approved": False,  # faculty require admin approval
                "first_name": "",
                "last_name": "",
            }).execute()

            if not insert_response.data:
                logger.error(f"Faculty profile insert returned no data for {user.email}")
                return None

            logger.info(f"Created pending faculty profile for {user.email}")
            BaseService.clear_cache()
            return FacultyService.get_profile(user.id)

        except Exception as e:
            logger.exception(f"Failed to create faculty profile for {user.email}")
            return None

    @staticmethod
    def update_profile(user_id: str, updates: dict) -> bool:
        """
        Updates mutable profile fields.
        Returns True on success, False on failure.
        """
        try:
            response = (
                supabase
                .table("profiles")
                .update(updates)
                .eq("id", user_id)
                .execute()
            )
            if response.data:
                BaseService.clear_cache()
                logger.info(f"Profile updated for user_id={user_id}")
                return True
            logger.warning(f"Profile update for user_id={user_id} returned no data.")
            return False
        except Exception as e:
            logger.exception(f"Failed to update profile for user_id={user_id}")
            return False
