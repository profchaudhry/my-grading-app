import logging
from services.supabase_client import supabase
from services.base_service import BaseService
from services.faculty_service import FacultyService
from services.student_service import StudentService

logger = logging.getLogger("sylemax.auth_service")


class AuthService(BaseService):

    @staticmethod
    def login(email: str, password: str) -> dict | None:
        """
        Authenticates a user via Supabase and loads their profile.
        Returns {"user": ..., "profile": ...} on success, or None on failure.
        """
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })

            if not response or not response.user:
                logger.warning(f"Login failed: no user returned for {email}")
                return None

            user = response.user

            profile_response = (
                supabase
                .table("profiles")
                .select("*")
                .eq("id", user.id)
                .execute()
            )

            if profile_response.data:
                profile = profile_response.data[0]
            else:
                # No profile found → auto-create as student
                logger.info(f"No profile found for {user.email}. Creating default student profile.")
                profile = StudentService.ensure_profile_exists(user, role="student")

            if not profile:
                logger.error(f"Profile could not be created or retrieved for {user.email}")
                return None

            logger.info(f"Login successful for {user.email} with role '{profile.get('role')}'")
            return {"user": user, "profile": profile}

        except Exception as e:
            logger.exception(f"Login error for {email}")
            return None

    @staticmethod
    def register_faculty(email: str, password: str) -> bool:
        """
        Registers a new faculty user in Supabase Auth and creates a pending profile.
        Returns True on success, False on failure.
        """
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })

            if not response or not response.user:
                logger.warning(f"Faculty registration failed: no user returned for {email}")
                return False

            user = response.user

            profile = FacultyService.ensure_profile_exists(user, role="faculty")

            if not profile:
                logger.error(f"Faculty profile creation failed for {email}")
                return False

            logger.info(f"Faculty registration submitted for {email}")
            return True

        except Exception as e:
            logger.exception(f"Faculty registration error for {email}")
            return False

    @staticmethod
    def logout() -> None:
        """Signs out from Supabase and is safe to call even if already signed out."""
        try:
            supabase.auth.sign_out()
        except Exception:
            pass  # Sign-out errors are non-critical; session will be cleared by caller
