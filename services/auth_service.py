from services.supabase_client import supabase
from services.base_service import BaseService
from services.faculty_service import FacultyService
from services.student_service import StudentService
import logging


class AuthService(BaseService):

    @staticmethod
    def login(email, password):
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not response or not response.user:
                return None

            user = response.user

            # Fetch existing profile
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
                # If no profile exists → default student
                profile = StudentService.ensure_profile_exists(user)

            return {"user": user, "profile": profile}

        except Exception as e:
            logging.exception(e)
            return None

    @staticmethod
    def register_faculty(email, password):
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if not response or not response.user:
                return None

            user = response.user

            FacultyService.ensure_profile_exists(user, role="faculty")

            return response

        except Exception as e:
            logging.exception(e)
            return None
