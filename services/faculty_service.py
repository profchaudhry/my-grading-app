import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL


class FacultyService(BaseService):

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_profile(user_id):
        try:
            response = (
                supabase
                .table("profiles")
                .select("*")
                .eq("id", user_id)
                .execute()
            )
            data = response.data
            if data and len(data) > 0:
                return data[0]
            return None
        except Exception:
            return None

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_assigned_courses(faculty_id):
        try:
            response = (
                supabase
                .table("course_assignments")
                .select("courses(title,code,semester)")
                .eq("faculty_id", faculty_id)
                .execute()
            )
            return response.data or []
        except Exception:
            return []

    @staticmethod
    def update_profile(user_id, data):
        try:
            supabase.table("profiles").update(data).eq("id", user_id).execute()
            FacultyService.clear_cache()
        except Exception:
            pass

    @staticmethod
    def ensure_profile_exists(user, role="faculty"):
        """Auto-create profile if missing"""
        profile = FacultyService.get_profile(user.id)
        if profile is None:
            supabase.table("profiles").insert({
                "id": user.id,
                "email": user.email,
                "role": role,
                "approved": False
            }).execute()
        return FacultyService.get_profile(user.id)
