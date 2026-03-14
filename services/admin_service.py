import logging
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL
from services.cache_utils import ttl_cache

logger = logging.getLogger("sylemax.admin_service")


@ttl_cache(ttl=CACHE_TTL)
def _cached_get_all_users() -> list:
    try:
        response = (
            supabase
            .table("profiles")
            .select("*")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception("Failed to fetch all users.")
        return []


@ttl_cache(ttl=CACHE_TTL)
def _cached_get_pending_faculty() -> list:
    try:
        response = (
            supabase
            .table("profiles")
            .select("*")
            .eq("role", "faculty")
            .eq("approved", False)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception("Failed to fetch pending faculty.")
        return []


@ttl_cache(ttl=CACHE_TTL)
def _cached_get_system_metrics() -> dict:
    try:
        response = (
            supabase
            .table("profiles")
            .select("role")
            .execute()
        )
        users = response.data or []
        return {
            "total_users": len(users),
            "faculty":  sum(1 for u in users if u.get("role") == "faculty"),
            "students": sum(1 for u in users if u.get("role") == "student"),
            "admins":   sum(1 for u in users if u.get("role") == "admin"),
        }
    except Exception as e:
        logger.exception("Failed to fetch system metrics.")
        return {"total_users": 0, "faculty": 0, "students": 0, "admins": 0}


class AdminService(BaseService):

    @staticmethod
    def get_all_users() -> list:
        return _cached_get_all_users()

    @staticmethod
    def get_faculty_users() -> list:
        return [u for u in _cached_get_all_users() if u.get("role") == "faculty"]

    @staticmethod
    def get_student_users() -> list:
        return [u for u in _cached_get_all_users() if u.get("role") == "student"]

    @staticmethod
    def get_pending_faculty() -> list:
        return _cached_get_pending_faculty()

    @staticmethod
    def get_system_metrics() -> dict:
        return _cached_get_system_metrics()

    @staticmethod
    def update_profile(user_id: str, updates: dict) -> bool:
        """Update any profile fields for any user."""
        try:
            response = (
                supabase
                .table("profiles")
                .update(updates)
                .eq("id", user_id)
                .execute()
            )
            if response.data:
                AdminService.clear_cache()
                logger.info(f"Profile updated by admin for user_id={user_id}")
                return True
            logger.warning(f"Profile update returned no data for user_id={user_id}")
            return False
        except Exception as e:
            AdminService.handle_error(e, context="update_profile")
            return False

    @staticmethod
    def delete_user(user_id: str) -> bool:
        """
        Deletes a user from auth.users (cascades to profiles automatically).
        Uses the Supabase admin API via service role.
        """
        try:
            supabase.auth.admin.delete_user(user_id)
            AdminService.clear_cache()
            logger.info(f"User deleted by admin: user_id={user_id}")
            return True
        except Exception as e:
            AdminService.handle_error(e, context="delete_user")
            return False

    @staticmethod
    def approve_faculty(user_id: str) -> bool:
        try:
            response = (
                supabase
                .table("profiles")
                .update({"approved": True})
                .eq("id", user_id)
                .execute()
            )
            if response.data:
                AdminService.clear_cache()
                logger.info(f"Faculty approved: user_id={user_id}")
                return True
            return False
        except Exception as e:
            AdminService.handle_error(e, context="approve_faculty")
            return False

    @staticmethod
    def reject_faculty(user_id: str) -> bool:
        try:
            supabase.table("profiles").delete().eq("id", user_id).execute()
            AdminService.clear_cache()
            logger.info(f"Faculty rejected: user_id={user_id}")
            return True
        except Exception as e:
            AdminService.handle_error(e, context="reject_faculty")
            return False

    @staticmethod
    def update_role(user_id: str, new_role: str) -> bool:
        from core.permissions import VALID_ROLES
        if new_role not in VALID_ROLES:
            logger.warning(f"Invalid role '{new_role}' for user_id={user_id}")
            return False
        try:
            response = (
                supabase
                .table("profiles")
                .update({"role": new_role})
                .eq("id", user_id)
                .execute()
            )
            if response.data:
                AdminService.clear_cache()
                return True
            return False
        except Exception as e:
            AdminService.handle_error(e, context="update_role")
            return False
