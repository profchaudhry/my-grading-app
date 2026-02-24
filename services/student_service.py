import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL


class StudentService(BaseService):

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
    def ensure_profile_exists(user, role="student"):
        """Auto-create profile if missing"""
        profile = StudentService.get_profile(user.id)
        if profile is None:
            supabase.table("profiles").insert({
                "id": user.id,
                "email": user.email,
                "role": role,
                "approved": True  # students auto-approved
            }).execute()
        return StudentService.get_profile(user.id)
