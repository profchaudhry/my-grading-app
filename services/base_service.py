import logging
import streamlit as st

logger = logging.getLogger("sylemax.base_service")


class BaseService:

    @staticmethod
    def clear_cache() -> None:
        """Clears all Streamlit cached data. Safe to call even if cache is empty."""
        try:
            st.cache_data.clear()
            logger.info("Cache cleared.")
        except Exception:
            logger.warning("Cache clear attempted but failed silently.")

    @staticmethod
    def handle_error(e: Exception, context: str = "") -> None:
        """
        Logs the exception with optional context.
        Does NOT re-raise — callers decide whether to propagate.
        """
        msg = f"Error in {context}: {e}" if context else str(e)
        logger.exception(msg)
