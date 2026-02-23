from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL
import streamlit as st


class AdminService(BaseService):

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_pending_faculty():
        return supabase.table("profiles")\
            .select("*")\
            .eq("role", "faculty")\
            .eq("approved", False)\
            .execute().data

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_all_users():
        return supabase.table("profiles")\
            .select("id, email, role, approved")\
            .execute().data

    @staticmethod
    def approve_faculty(user_id):
        supabase.table("profiles")\
            .update({"approved": True})\
            .eq("id", user_id)\
            .execute()

        AdminService.clear_cache()

    @staticmethod
    def update_role(user_id, new_role):
        supabase.table("profiles")\
            .update({"role": new_role})\
            .eq("id", user_id)\
            .execute()

        AdminService.clear_cache()
