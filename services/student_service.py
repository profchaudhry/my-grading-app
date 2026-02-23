from services.supabase_client import supabase
import streamlit as st

@st.cache_data(ttl=30)
def get_student_profile(user_id):
    return supabase.table("profiles")\
        .select("*")\
        .eq("id", user_id)\
        .single()\
        .execute().data
