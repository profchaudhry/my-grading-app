from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
import streamlit as st
import logging

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase environment variables are not configured.")
    st.stop()

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logging.exception(e)
    st.error("Failed to connect to Supabase.")
    st.stop()
