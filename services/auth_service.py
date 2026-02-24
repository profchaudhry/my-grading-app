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

            # Fetch profile — trigger guarantees it exists after sign_up
            profile_response = (
                supabase
                .table("profiles")
                .select("*")
                .eq("id", user.id)
                .execute()
            )

            if not profile_response.data:
                logger.error(f"No profile found for authenticated user {email}")
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
    def register_faculty(email: str, password: str) -> bool:
        """
        Registers a new faculty user.

        Flow:
          1. supabase.auth.sign_up() creates the auth user.
          2. The DB trigger immediately inserts a default 'student' profile.
          3. We update that profile to role='faculty', approved=False.

        Returns True on success, False on any failure.
        """
        try:
            # Step 1: Create auth user
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })

            if not response or not response.user:
                logger.warning(f"Faculty sign_up failed: no user returned for {email}")
                return False

            user = response.user

            # Step 2: Update the trigger-created profile to faculty (pending approval)
            update_response = (
                supabase
                .table("profiles")
                .update({
                    "role": "faculty",
                    "approved": False,
                    "first_name": "",
                    "last_name": "",
                })
                .eq("id", user.id)
                .execute()
            )

            if not update_response.data:
                # Profile row may not exist yet if trigger hasn't fired —
                # fall back to an upsert to guarantee the row is correct.
                logger.warning(
                    f"Profile update returned no data for {email}. "
                    "Attempting upsert fallback."
                )
                upsert_response = (
                    supabase
                    .table("profiles")
                    .upsert({
                        "id": user.id,
                        "email": email,
                        "role": "faculty",
                        "approved": False,
                        "first_name": "",
                        "last_name": "",
                    })
                    .execute()
                )

                if not upsert_response.data:
                    logger.error(f"Upsert fallback also failed for {email}")
                    return False

            # Clear cache so pending faculty list reflects the new entry
            AuthService.clear_cache()
            logger.info(f"Faculty registration submitted successfully for {email}")
            return True

        except Exception as e:
            logger.exception(f"Faculty registration error for {email}")
            return False

    # ==========================================================
    # STUDENT REGISTRATION (if needed in future)
    # ==========================================================
    @staticmethod
    def register_student(email: str, password: str) -> bool:
        """
        Registers a student. The DB trigger auto-creates a student profile
        with approved=True, so no profile update is needed.

        Returns True on success, False on failure.
        """
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })

            if not response or not response.user:
                logger.warning(f"Student sign_up failed: no user returned for {email}")
                return False

            logger.info(f"Student registered successfully for {email}")
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
        """
        Signs out from Supabase. Safe to call even if already signed out.
        Session state cleanup is handled by the caller (layout/router).
        """
        try:
            supabase.auth.sign_out()
            logger.info("User signed out from Supabase.")
        except Exception:
            # Non-critical — local session will be cleared regardless
            logger.warning("Supabase sign_out call failed (may already be signed out).")
