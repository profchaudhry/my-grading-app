import logging
from services.supabase_client import supabase
from services.base_service import BaseService

logger = logging.getLogger("sylemax.auth_service")


class AuthService(BaseService):

    # ==========================================================
    # LOGIN
    # ==========================================================
    @staticmethod
    def login(email: str, password: str) -> dict | None:
        try:
            response = supabase.auth.sign_in_with_password({
                "email":    email,
                "password": password,
            })

            user = getattr(response, "user", None)
            if not user or not getattr(user, "id", None):
                logger.warning(f"Login failed: no user returned for {email}")
                return None

            profile_response = (
                supabase
                .table("profiles")
                .select("*")
                .eq("id", user.id)
                .execute()
            )

            if not profile_response.data:
                logger.error(f"No profile found for {email}")
                return None

            profile = profile_response.data[0]
            logger.info(f"Login successful for {email} | role='{profile.get('role')}'")
            return {"user": user, "profile": profile}

        except Exception as e:
            logger.exception(f"Login error for {email}")
            return None

    # ==========================================================
    # FACULTY REGISTRATION
    # ==========================================================
    @staticmethod
    def register_faculty(
        email:       str,
        password:    str,
        first_name:  str = "",
        last_name:   str = "",
        employee_id: str = "",
    ) -> bool:
        """
        Registers a faculty member.
        Captures full name and employee ID at registration time.
        These can only be edited by admin afterwards.
        """
        try:
            # Step 1: Create auth user
            response = supabase.auth.sign_up({
                "email":    email,
                "password": password,
            })

            user = getattr(response, "user", None)
            if not user or not getattr(user, "id", None):
                logger.warning(f"Faculty sign_up failed for {email}")
                return False

            # Step 2: Update the trigger-created profile with all registration data
            update_response = (
                supabase
                .table("profiles")
                .update({
                    "first_name":  first_name,
                    "last_name":   last_name,
                    "employee_id": employee_id,
                    "role":        "faculty",
                    "approved":    False,
                })
                .eq("id", user.id)
                .execute()
            )

            if not update_response.data:
                # Fallback upsert
                supabase.table("profiles").upsert({
                    "id":          user.id,
                    "email":       email,
                    "first_name":  first_name,
                    "last_name":   last_name,
                    "employee_id": employee_id,
                    "role":        "faculty",
                    "approved":    False,
                }).execute()

            AuthService.clear_cache()
            logger.info(f"Faculty registration submitted for {email}")
            return True

        except Exception as e:
            logger.exception(f"Faculty registration error for {email}")
            return False

    # ==========================================================
    # STUDENT REGISTRATION (admin/bulk only)
    # ==========================================================
    @staticmethod
    def register_student(email: str, password: str) -> bool:
        try:
            response = supabase.auth.sign_up({
                "email":    email,
                "password": password,
            })
            user = getattr(response, "user", None)
            if not user or not getattr(user, "id", None):
                return False
            AuthService.clear_cache()
            return True
        except Exception as e:
            logger.exception(f"Student registration error for {email}")
            return False

    # ==========================================================
    # LOGOUT
    # ==========================================================
    @staticmethod
    def logout() -> None:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
