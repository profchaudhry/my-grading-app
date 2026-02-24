import logging
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL

logger = logging.getLogger("sylemax.department_service")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cached_get_all_departments() -> list:
    try:
        response = (
            supabase
            .table("departments")
            .select("*")
            .order("name")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.exception("Failed to fetch departments.")
        return []


class DepartmentService(BaseService):

    @staticmethod
    def get_all() -> list:
        return _cached_get_all_departments()

    @staticmethod
    def create(name: str, code: str) -> bool:
        try:
            response = (
                supabase
                .table("departments")
                .insert({"name": name.strip(), "code": code.strip().upper()})
                .execute()
            )
            if response.data:
                DepartmentService.clear_cache()
                logger.info(f"Department created: {name} ({code})")
                return True
            return False
        except Exception as e:
            logger.exception(f"Failed to create department: {name}")
            return False

    @staticmethod
    def update(dept_id: str, name: str, code: str) -> bool:
        try:
            response = (
                supabase
                .table("departments")
                .update({"name": name.strip(), "code": code.strip().upper()})
                .eq("id", dept_id)
                .execute()
            )
            if response.data:
                DepartmentService.clear_cache()
                return True
            return False
        except Exception as e:
            logger.exception(f"Failed to update department: {dept_id}")
            return False

    @staticmethod
    def delete(dept_id: str) -> bool:
        try:
            supabase.table("departments").delete().eq("id", dept_id).execute()
            DepartmentService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Failed to delete department: {dept_id}")
            return False
