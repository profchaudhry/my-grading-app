import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService
from config import CACHE_TTL


class AdminService(BaseService):

    # ==========================================================
    # GET ALL USERS
    # ==========================================================
    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_all_users():
        try:
            response = (
                supabase
                .table("profiles")
                .select("id, email, role, approved")
                .execute()
            )

            if response.data:
                return response.data

            return []

        except Exception as e:
            AdminService.handle_error(e)
            return []

    # ==========================================================
    # GET PENDING FACULTY APPROVALS
    # ==========================================================
    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_pending_faculty():
        try:
            response = (
                supabase
                .table("profiles")
                .select("id, email, role, approved")
                .eq("role", "faculty")
                .eq("approved", False)
                .execute()
            )

            if response.data:
                return response.data

            return []

        except Exception as e:
            AdminService.handle_error(e)
            return []

    # ==========================================================
    # APPROVE FACULTY
    # ==========================================================
    @staticmethod
    def approve_faculty(user_id: str):
        try:
            supabase.table("profiles")\
                .update({"approved": True})\
                .eq("id", user_id)\
                .execute()

            # Clear cache after mutation
            AdminService.clear_cache()

            return True

        except Exception as e:
            AdminService.handle_error(e)
            return False

    # ==========================================================
    # REJECT FACULTY (OPTIONAL ENTERPRISE ADDITION)
    # ==========================================================
    @staticmethod
    def reject_faculty(user_id: str):
        try:
            supabase.table("profiles")\
                .delete()\
                .eq("id", user_id)\
                .execute()

            AdminService.clear_cache()
            return True

        except Exception as e:
            AdminService.handle_error(e)
            return False

    # ==========================================================
    # UPDATE USER ROLE
    # ==========================================================
    @staticmethod
    def update_role(user_id: str, new_role: str):
        try:
            supabase.table("profiles")\
                .update({"role": new_role})\
                .eq("id", user_id)\
                .execute()

            AdminService.clear_cache()
            return True

        except Exception as e:
            AdminService.handle_error(e)
            return False

    # ==========================================================
    # SYSTEM METRICS
    # ==========================================================
    @staticmethod
    @st.cache_data(ttl=CACHE_TTL)
    def get_system_metrics():
        try:
            response = (
                supabase
                .table("profiles")
                .select("role")
                .execute()
            )

            users = response.data or []

            total_users = len(users)
            total_faculty = len([u for u in users if u["role"] == "faculty"])
            total_students = len([u for u in users if u["role"] == "student"])
            total_admins = len([u for u in users if u["role"] == "admin"])

            return {
                "total_users": total_users,
                "faculty": total_faculty,
                "students": total_students,
                "admins": total_admins,
            }

        except Exception as e:
            AdminService.handle_error(e)
            return {
                "total_users": 0,
                "faculty": 0,
                "students": 0,
                "admins": 0,
            }
