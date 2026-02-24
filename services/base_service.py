import streamlit as st
import logging


class BaseService:

    @staticmethod
    def clear_cache():
        try:
            st.cache_data.clear()
        except Exception:
            pass

    @staticmethod
    def handle_error(e):
        logging.exception(e)
        raise e
