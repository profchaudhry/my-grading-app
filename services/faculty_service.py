from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL
import streamlit as st

class FacultyService(BaseService):

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_profile(user_id):
        return supabase.table("profiles")\
            .select("*")\
            .eq("id", user_id)\
            .single()\
            .execute().data

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_assigned_courses(faculty_id):
        return supabase.table("course_assignments")\
            .select("courses(title,code,semester)")\
            .eq("faculty_id", faculty_id)\
            .execute().data

    @staticmethod
    def update_profile(user_id, data):
        supabase.table("profiles")\
            .update(data)\
            .eq("id", user_id)\
            .execute()

        FacultyService.clear_cache()
