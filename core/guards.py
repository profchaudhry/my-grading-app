import streamlit as st
from core.permissions import ROLE_PERMISSIONS

def require_role(allowed_roles):
    def decorator(func):
        def wrapper(*args, **kwargs):
            role = st.session_state.get("role")
            if role not in allowed_roles:
                st.error("Unauthorized access")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_approval(profile):
    if profile.get("approved") is False:
        st.warning("Awaiting admin approval.")
        st.stop()
