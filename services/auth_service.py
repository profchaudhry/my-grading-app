from services.supabase_client import supabase
from services.base_service import BaseService
from services.faculty_service import FacultyService
from services.student_service import StudentService


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

            # Ensure profile exists
            profile = FacultyService.ensure_profile_exists(user)
            if profile:
                return {"user": user, "profile": profile}
            return {"user": user, "profile": None}

        except Exception:
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

            # Create faculty profile
            FacultyService.ensure_profile_exists(user, role="faculty")
            return response

        except Exception:
            return None
