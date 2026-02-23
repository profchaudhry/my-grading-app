import streamlit as st
import logging

class BaseService:

    @staticmethod
    def clear_cache():
        st.cache_data.clear()

    @staticmethod
    def handle_error(e):
        logging.exception(e)
        raise e
