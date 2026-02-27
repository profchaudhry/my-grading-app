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

            # Extract session tokens for persistence
            session = getattr(response, "session", None)
            access_token  = getattr(session, "access_token",  None) if session else None
            refresh_token = getattr(session, "refresh_token", None) if session else None

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
            return {
                "user":          user,
                "profile":       profile,
                "access_token":  access_token,
                "refresh_token": refresh_token,
            }

        except Exception as e:
            logger.exception(f"Login error for {email}")
            return None

    # ==========================================================
    # RESTORE SESSION (called on every page load)
    # ==========================================================
    @staticmethod
    def restore_session(access_token: str, refresh_token: str) -> dict | None:
        """
        Restore a Supabase session from stored tokens.
        Returns {"user": user, "profile": profile} on success, None on failure.
        """
        try:
            response = supabase.auth.set_session(access_token, refresh_token)
            user = getattr(response, "user", None)
            if not user or not getattr(user, "id", None):
                return None

            # Get fresh tokens in case they were refreshed
            session = getattr(response, "session", None)
            new_access  = getattr(session, "access_token",  access_token)  if session else access_token
            new_refresh = getattr(session, "refresh_token", refresh_token) if session else refresh_token

            profile_response = (
                supabase
                .table("profiles")
                .select("*")
                .eq("id", user.id)
                .execute()
            )

            if not profile_response.data:
                return None

            profile = profile_response.data[0]
            logger.info(f"Session restored for user {user.id} | role='{profile.get('role')}'")
            return {
                "user":          user,
                "profile":       profile,
                "access_token":  new_access,
                "refresh_token": new_refresh,
            }

        except Exception as e:
            logger.warning(f"Session restore failed: {e}")
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
        try:
            response = supabase.auth.sign_up({
                "email":    email,
                "password": password,
            })

            user = getattr(response, "user", None)
            if not user or not getattr(user, "id", None):
                logger.warning(f"Faculty sign_up failed for {email}")
                return False

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
