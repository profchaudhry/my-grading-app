from services.supabase_client import supabase
import streamlit as st

@st.cache_data(ttl=30)
def get_assigned_courses(faculty_id):
    return supabase.table("course_assignments")\
        .select("courses(title,code,semester)")\
        .eq("faculty_id", faculty_id)\
        .execute().data

@st.cache_data(ttl=30)
def get_profile(user_id):
    return supabase.table("profiles")\
        .select("*")\
        .eq("id", user_id)\
        .single()\
        .execute().data

def update_profile(user_id, data):
    supabase.table("profiles")\
        .update(data)\
        .eq("id", user_id)\
        .execute()
