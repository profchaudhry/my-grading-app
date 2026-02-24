import logging
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL

logger = logging.getLogger("sylemax.admin_service")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_all_users() -> list:
    try:
        response = (
            supabase
            .table("profiles")
            .select("id, email, role, approved, first_name, last_name")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception("Failed to fetch all users.")
        return []


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_pending_faculty() -> list:
    try:
        response = (
            supabase
            .table("profiles")
            .select("id, email, role, approved")
            .eq("role", "faculty")
            .eq("approved", False)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception("Failed to fetch pending faculty.")
        return []


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
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
            "faculty": sum(1 for u in users if u.get("role") == "faculty"),
            "students": sum(1 for u in users if u.get("role") == "student"),
            "admins": sum(1 for u in users if u.get("role") == "admin"),
        }
    except Exception as e:
        logger.exception("Failed to fetch system metrics.")
        return {"total_users": 0, "faculty": 0, "students": 0, "admins": 0}


class AdminService(BaseService):

    @staticmethod
    def get_all_users() -> list:
        return _cached_get_all_users()

    @staticmethod
    def get_pending_faculty() -> list:
        return _cached_get_pending_faculty()

    @staticmethod
    def get_system_metrics() -> dict:
        return _cached_get_system_metrics()

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
            logger.warning(f"Approve faculty returned no data for user_id={user_id}")
            return False
        except Exception as e:
            AdminService.handle_error(e, context="approve_faculty")
            return False

    @staticmethod
    def reject_faculty(user_id: str) -> bool:
        try:
            response = (
                supabase
                .table("profiles")
                .delete()
                .eq("id", user_id)
                .execute()
            )
            if response.data is not None:
                AdminService.clear_cache()
                logger.info(f"Faculty rejected and removed: user_id={user_id}")
                return True
            logger.warning(f"Reject faculty returned unexpected response for user_id={user_id}")
            return False
        except Exception as e:
            AdminService.handle_error(e, context="reject_faculty")
            return False

    @staticmethod
    def update_role(user_id: str, new_role: str) -> bool:
        from core.permissions import VALID_ROLES
        if new_role not in VALID_ROLES:
            logger.warning(f"Attempted to set invalid role '{new_role}' for user_id={user_id}")
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
                logger.info(f"Role updated to '{new_role}' for user_id={user_id}")
                return True
            logger.warning(f"Role update returned no data for user_id={user_id}")
            return False
        except Exception as e:
            AdminService.handle_error(e, context="update_role")
            return False
