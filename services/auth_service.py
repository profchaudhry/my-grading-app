from services.supabase_client import supabase
from services.base_service import BaseService
from services.faculty_service import FacultyService
from services.student_service import StudentService
import logging


class AuthService(BaseService):

    # ==========================================================
    # LOGIN
    # ==========================================================
    @staticmethod
    def login(email: str, password: str):
        try:
            # Attempt Supabase login
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not response or not response.user:
                logging.warning("Login failed: No user returned.")
                return None

            user = response.user

            # Fetch profile from DB
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
                # If profile does not exist → default to student
                logging.info(f"No profile found. Creating student profile for {user.email}")
                profile = StudentService.ensure_profile_exists(user)

            return {
                "user": user,
                "profile": profile
            }

        except Exception as e:
            logging.exception("Login error occurred.")
            return None

    # ==========================================================
    # FACULTY REGISTRATION
    # ==========================================================
    @staticmethod
    def register_faculty(email: str, password: str):
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if not response or not response.user:
                logging.warning("Faculty registration failed.")
                return None

            user = response.user

            # Create faculty profile (awaiting approval)
            FacultyService.ensure_profile_exists(user, role="faculty")

            logging.info(f"Faculty registration submitted for {email}")

            return response

        except Exception as e:
            logging.exception("Faculty registration error.")
            return None
