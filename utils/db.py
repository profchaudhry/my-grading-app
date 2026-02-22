import streamlit as st
from supabase import create_client
import pandas as pd

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=60)
def load_courses():
    res = supabase.table("courses").select("*").execute()
    return res.data if res.data else []

@st.cache_data(ttl=60)
def load_faculty():
    res = supabase.table("profiles")\
        .select("*")\
        .in_("role", ["faculty", "faculty_pro"])\
        .execute()
    return res.data if res.data else []

@st.cache_data(ttl=60)
def load_students():
    res = supabase.table("students").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def get_profile(user_id):
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None
