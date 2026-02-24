import logging
import streamlit as st
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("sylemax.supabase")

_supabase_client: Client | None = None


def get_supabase() -> Client:
    """
    Returns a singleton Supabase client.
    Initializes it on first call and caches it in module scope.
    Stops the app with a user-friendly error if connection fails.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully.")
        return _supabase_client
    except Exception as e:
        logger.exception("Failed to initialize Supabase client.")
        st.error("Unable to connect to the database. Please contact support.")
        st.stop()


# Module-level convenience reference — use get_supabase() in services
supabase: Client = get_supabase()
