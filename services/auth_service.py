from services.supabase_client import supabase
from services.base_service import BaseService

class AuthService(BaseService):

    @staticmethod
    def login(email, password):
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return response
        except Exception as e:
            AuthService.handle_error(e)

    @staticmethod
    def register_faculty(email, password):
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            supabase.table("profiles").insert({
                "id": response.user.id,
                "email": email,
                "role": "faculty",
                "approved": False
            }).execute()

            return response
        except Exception as e:
            AuthService.handle_error(e)
