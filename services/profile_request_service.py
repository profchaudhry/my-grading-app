"""
ProfileRequestService — manages student requests to update locked profile fields.

Required Supabase table (run once in SQL editor):

    create table profile_change_requests (
        id          uuid primary key default gen_random_uuid(),
        student_id  uuid not null references profiles(id) on delete cascade,
        field_name  text not null,          -- e.g. 'date_of_birth', 'personal_email'
        old_value   text,
        new_value   text not null,
        status      text not null default 'pending',  -- pending | approved | rejected
        admin_note  text,
        created_at  timestamptz default now(),
        updated_at  timestamptz default now()
    );

    -- Index for fast student/status lookups
    create index on profile_change_requests(student_id, status);
"""
import logging
from services.supabase_client import supabase
from services.base_service import BaseService

logger = logging.getLogger("sylemax.profile_request_service")

TABLE = "profile_change_requests"


class ProfileRequestService(BaseService):

    @staticmethod
    def submit_request(student_id: str, field_name: str,
                       new_value: str, old_value: str = "") -> tuple[bool, str]:
        """Student submits a change request for a locked field."""
        try:
            # Check no pending request already exists for this field
            existing = supabase.table(TABLE)\
                .select("id")\
                .eq("student_id", student_id)\
                .eq("field_name", field_name)\
                .eq("status", "pending")\
                .execute()
            if existing.data:
                return False, "A pending request for this field already exists. Please wait for admin review."

            supabase.table(TABLE).insert({
                "student_id": student_id,
                "field_name": field_name,
                "old_value":  old_value or "",
                "new_value":  new_value,
                "status":     "pending",
            }).execute()
            return True, "Request submitted. An admin will review it shortly."
        except Exception as e:
            logger.exception(f"Failed to submit profile request: {student_id} / {field_name}")
            return False, str(e)

    @staticmethod
    def get_student_requests(student_id: str) -> list:
        """Get all requests for a student."""
        try:
            r = supabase.table(TABLE)\
                .select("*")\
                .eq("student_id", student_id)\
                .order("created_at", desc=True)\
                .execute()
            return r.data or []
        except Exception as e:
            logger.exception(f"Failed to fetch requests for student {student_id}")
            return []

    @staticmethod
    def get_pending_requests() -> list:
        """Get all pending requests — for admin review."""
        try:
            r = supabase.table(TABLE)\
                .select("*, profiles(id, full_name, first_name, last_name, enrollment_number, email)")\
                .eq("status", "pending")\
                .order("created_at", desc=False)\
                .execute()
            return r.data or []
        except Exception as e:
            logger.exception("Failed to fetch pending profile requests")
            return []

    @staticmethod
    def get_all_requests() -> list:
        """Get all requests (all statuses) — for admin view."""
        try:
            r = supabase.table(TABLE)\
                .select("*, profiles(id, full_name, first_name, last_name, enrollment_number, email)")\
                .order("created_at", desc=True)\
                .execute()
            return r.data or []
        except Exception as e:
            logger.exception("Failed to fetch all profile requests")
            return []

    @staticmethod
    def approve_request(request_id: str, admin_note: str = "") -> tuple[bool, str]:
        """Admin approves a request — applies the change to the profile."""
        try:
            # Fetch the request
            r = supabase.table(TABLE)\
                .select("*")\
                .eq("id", request_id)\
                .execute()
            if not r.data:
                return False, "Request not found."
            req = r.data[0]

            # Apply the change to profiles
            from services.profile_service import ProfileService
            ok = ProfileService.update_profile(req["student_id"], {
                req["field_name"]: req["new_value"]
            })
            if not ok:
                return False, "Failed to apply change to profile."

            # Mark request approved
            supabase.table(TABLE).update({
                "status":     "approved",
                "admin_note": admin_note,
                "updated_at": "now()",
            }).eq("id", request_id).execute()

            return True, f"Change approved and applied: {req['field_name']} → {req['new_value']}"
        except Exception as e:
            logger.exception(f"Failed to approve request {request_id}")
            return False, str(e)

    @staticmethod
    def reject_request(request_id: str, admin_note: str = "") -> tuple[bool, str]:
        """Admin rejects a request."""
        try:
            supabase.table(TABLE).update({
                "status":     "rejected",
                "admin_note": admin_note or "Rejected by admin.",
                "updated_at": "now()",
            }).eq("id", request_id).execute()
            return True, "Request rejected."
        except Exception as e:
            logger.exception(f"Failed to reject request {request_id}")
            return False, str(e)

    @staticmethod
    def table_exists() -> bool:
        """Check if the profile_change_requests table exists."""
        try:
            supabase.table(TABLE).select("id").limit(1).execute()
            return True
        except Exception:
            return False
