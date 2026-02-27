import logging
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL

logger = logging.getLogger("sylemax.semester_service")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_all_semesters() -> list:
    try:
        response = (
            supabase
            .table("semesters")
            .select("*")
            .order("start_date", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception("Failed to fetch semesters.")
        return []


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_active_semester() -> dict | None:
    try:
        response = (
            supabase
            .table("semesters")
            .select("*")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.exception("Failed to fetch active semester.")
        return None


class SemesterService(BaseService):

    @staticmethod
    def get_all() -> list:
        return _cached_get_all_semesters()

    @staticmethod
    def get_active() -> dict | None:
        return _cached_get_active_semester()

    @staticmethod
    def create(name: str, start_date: str, end_date: str) -> bool:
        try:
            response = (
                supabase
                .table("semesters")
                .insert({
                    "name":       name.strip(),
                    "start_date": start_date,
                    "end_date":   end_date,
                    "is_active":  False,
                })
                .execute()
            )
            if response.data:
                SemesterService.clear_cache()
                logger.info(f"Semester created: {name}")
                return True
            return False
        except Exception as e:
            logger.exception(f"Failed to create semester: {name}")
            return False

    @staticmethod
    def set_active(semester_id: str) -> bool:
        """
        Deactivates ALL semesters first, then activates the selected one.
        Uses two separate queries to avoid RLS or filter issues.
        """
        try:
            # Step 1: Deactivate all semesters
            supabase.table("semesters")\
                .update({"is_active": False})\
                .neq("id", "00000000-0000-0000-0000-000000000000")\
                .execute()

            # Step 2: Activate the selected one
            response = (
                supabase
                .table("semesters")
                .update({"is_active": True})
                .eq("id", semester_id)
                .execute()
            )

            SemesterService.clear_cache()

            if response.data:
                logger.info(f"Semester activated: {semester_id}")
                return True

            # Even if data is empty, the update may have worked — verify
            verify = (
                supabase
                .table("semesters")
                .select("is_active")
                .eq("id", semester_id)
                .execute()
            )
            if verify.data and verify.data[0].get("is_active"):
                logger.info(f"Semester activation verified: {semester_id}")
                return True

            logger.warning(f"Semester activation unconfirmed for: {semester_id}")
            return False

        except Exception as e:
            logger.exception(f"Failed to activate semester: {semester_id}")
            return False

    @staticmethod
    @staticmethod
    def update(semester_id: str, data: dict) -> bool:
        try:
            r = supabase.table("semesters").update(data).eq("id", semester_id).execute()
            SemesterService.clear_cache()
            return bool(r.data)
        except Exception:
            return False

    @staticmethod
    def delete(semester_id: str) -> bool:
        try:
            supabase.table("semesters").delete().eq("id", semester_id).execute()
            SemesterService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Failed to delete semester: {semester_id}")
            return False
