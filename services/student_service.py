import logging
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL

logger = logging.getLogger("sylemax.student_service")


# Module-level cached function (avoids @staticmethod + @st.cache_data conflict)
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_student_profile(user_id: str) -> dict | None:
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
        logger.exception(f"Failed to fetch student profile for user_id={user_id}")
        return None


class StudentService(BaseService):

    @staticmethod
    def get_profile(user_id: str) -> dict | None:
        return _cached_get_student_profile(user_id)

    @staticmethod
    def ensure_profile_exists(user, role: str = "student") -> dict | None:
        """
        Creates a profile for the user if one does not already exist.
        Returns the profile dict, or None if creation failed.
        """
        existing = StudentService.get_profile(user.id)
        if existing:
            return existing

        try:
            insert_response = supabase.table("profiles").insert({
                "id": user.id,
                "email": user.email,
                "role": role,
                "approved": True,  # students are auto-approved
                "first_name": "",
                "last_name": "",
            }).execute()

            if not insert_response.data:
                logger.error(f"Profile insert returned no data for user {user.email}")
                return None

            logger.info(f"Created {role} profile for {user.email}")

            # Bust cache so next read fetches the new row
            BaseService.clear_cache()
            return StudentService.get_profile(user.id)

        except Exception as e:
            logger.exception(f"Failed to create profile for user {user.email}")
            return None
