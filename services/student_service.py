from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL
import streamlit as st

class StudentService(BaseService):

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_profile(user_id):
        return supabase.table("profiles")\
            .select("*")\
            .eq("id", user_id)\
            .single()\
            .execute().data
