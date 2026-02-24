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
