import functools
from typing import List, Callable, Any
import streamlit as st
from core.permissions import VALID_ROLES


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Decorator that restricts access to a page function based on session role.
    Stops rendering and shows an error if the role is not permitted.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            role = st.session_state.get("role")

            if not role or role not in VALID_ROLES:
                st.error("Session invalid. Please log in again.")
                if st.button("Return to Login"):
                    st.session_state.clear()
                    st.rerun()
                st.stop()

            if role not in allowed_roles:
                st.error(f"Unauthorized: This page requires one of {allowed_roles}.")
                st.stop()

            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_approval(profile: dict) -> None:
    """
    Stops rendering if a faculty profile has not been approved yet.
    Shows a logout option so the user is not stuck.
    """
    if profile and profile.get("approved") is False:
        st.warning("Your account is awaiting admin approval. Please check back later.")
        if st.sidebar.button("Logout", key="approval_logout"):
            st.session_state.clear()
            st.rerun()
        st.stop()
