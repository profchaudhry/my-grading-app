import logging
from services.supabase_client import supabase
from services.base_service import BaseService

logger = logging.getLogger("sylemax.profile_service")


class ProfileService(BaseService):

    @staticmethod
    def get_profile(user_id: str) -> dict | None:
        """Fetch a single profile directly (no cache — for fresh reads)."""
        try:
            response = (
                supabase
                .table("profiles")
                .select("*")
                .eq("id", user_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception(f"Failed to fetch profile: {user_id}")
            return None

    @staticmethod
    def update_profile(user_id: str, updates: dict) -> bool:
        """Update allowed profile fields."""
        try:
            response = (
                supabase
                .table("profiles")
                .update(updates)
                .eq("id", user_id)
                .execute()
            )
            if response.data:
                ProfileService.clear_cache()
                logger.info(f"Profile updated for user_id={user_id}")
                return True
            logger.warning(f"Profile update returned no data for {user_id}")
            return False
        except Exception as e:
            logger.exception(f"Failed to update profile: {user_id}")
            return False

    @staticmethod
    def change_password(current_password: str, new_password: str, email: str) -> tuple[bool, str]:
        """
        Changes password by re-authenticating with current password first.
        Returns (success, error_message).
        """
        try:
            # Step 1: Verify current password by signing in
            verify = supabase.auth.sign_in_with_password({
                "email":    email,
                "password": current_password,
            })
            if not verify or not verify.user:
                return False, "Current password is incorrect."

            # Step 2: Update to new password
            supabase.auth.update_user({"password": new_password})
            logger.info(f"Password changed for {email}")
            return True, ""

        except Exception as e:
            err = str(e)
            if "Invalid login credentials" in err or "invalid_credentials" in err:
                return False, "Current password is incorrect."
            logger.exception(f"Password change failed for {email}")
            return False, "Password change failed. Please try again."
