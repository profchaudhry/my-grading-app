import logging
import re
import pandas as pd
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService

logger = logging.getLogger("sylemax.student_bulk_service")

TEMP_PASSWORD = "ChangeYourPassword"


class StudentBulkService(BaseService):

    @staticmethod
    def parse_excel(file) -> tuple[pd.DataFrame | None, str]:
        """
        Parses an uploaded Excel/CSV file.
        Expected columns: Enrollment Number, Full Name
        Returns (dataframe, error_message). error_message is "" on success.
        """
        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            # Normalize column names — strip spaces, lower case for matching
            df.columns = [c.strip() for c in df.columns]

            # Flexible column name matching
            col_map = {}
            for col in df.columns:
                lower = col.lower().replace(" ", "").replace("_", "").replace("-", "")
                if lower in ("enrollmentnumber", "enrollmentno", "enrollmentnum",
                             "enrollment", "rollno", "rollnumber", "regno",
                             "registrationnumber", "studentid"):
                    col_map["enrollment_number"] = col
                elif lower in ("fullname", "name", "studentname"):
                    col_map["full_name"] = col

            if "enrollment_number" not in col_map:
                return None, "Column 'Enrollment Number' not found. Please check your file."
            if "full_name" not in col_map:
                return None, "Column 'Full Name' not found. Please check your file."

            df = df.rename(columns={
                col_map["enrollment_number"]: "enrollment_number",
                col_map["full_name"]:         "full_name",
            })

            # Keep only needed columns
            df = df[["enrollment_number", "full_name"]].copy()

            # Clean up
            df["enrollment_number"] = df["enrollment_number"].astype(str).str.strip()
            df["full_name"]         = df["full_name"].astype(str).str.strip()

            # Drop empty rows
            df = df[df["enrollment_number"].notna() & (df["enrollment_number"] != "")]
            df = df[df["full_name"].notna()         & (df["full_name"] != "")]
            df = df.drop_duplicates(subset=["enrollment_number"])

            if df.empty:
                return None, "File is empty or has no valid rows."

            return df, ""

        except Exception as e:
            logger.exception("Failed to parse Excel file.")
            return None, f"Failed to read file: {str(e)}"

    @staticmethod
    def split_name(full_name: str) -> tuple[str, str]:
        """Splits 'John Smith' into ('John', 'Smith'). Handles single names."""
        parts = full_name.strip().split(" ", 1)
        first = parts[0] if len(parts) > 0 else full_name
        last  = parts[1] if len(parts) > 1 else ""
        return first, last

    @staticmethod
    def build_email(enrollment_number: str, domain: str) -> str:
        """
        Builds an email from enrollment number + domain.
        Enrollment numbers like 01-11111-011 are used as-is with @ prepended.
        """
        domain = domain.strip().lstrip("@")
        # Sanitize: replace spaces with dots for email safety
        safe_enroll = enrollment_number.strip().replace(" ", ".")
        return f"{safe_enroll}@{domain}"

    @staticmethod
    def check_existing_enrollments(enrollment_numbers: list[str]) -> set[str]:
        """Returns set of enrollment numbers that already have accounts."""
        try:
            response = (
                supabase
                .table("profiles")
                .select("enrollment_number")
                .in_("enrollment_number", enrollment_numbers)
                .execute()
            )
            return {r["enrollment_number"] for r in (response.data or [])}
        except Exception as e:
            logger.exception("Failed to check existing enrollments.")
            return set()

    @staticmethod
    def create_student_accounts(
        df: pd.DataFrame,
        domain: str,
        course_id: str | None = None,
        semester_id: str | None = None,
    ) -> tuple[int, int, list[str]]:
        """
        Creates student accounts from a parsed DataFrame.
        Returns (created_count, skipped_count, error_messages).
        """
        created, skipped = 0, 0
        errors = []

        existing = StudentBulkService.check_existing_enrollments(
            df["enrollment_number"].tolist()
        )

        for _, row in df.iterrows():
            enroll_num = str(row["enrollment_number"]).strip()
            full_name  = str(row["full_name"]).strip()

            if enroll_num in existing:
                skipped += 1
                logger.info(f"Skipping existing student: {enroll_num}")
                continue

            email = StudentBulkService.build_email(enroll_num, domain)
            first, last = StudentBulkService.split_name(full_name)

            try:
                # Step 1: Create auth user
                auth_response = supabase.auth.admin.create_user({
                    "email":            email,
                    "password":         TEMP_PASSWORD,
                    "email_confirm":    True,  # skip email confirmation
                    "user_metadata":    {"enrollment_number": enroll_num},
                })

                if not auth_response or not auth_response.user:
                    errors.append(f"{enroll_num}: Auth creation failed.")
                    continue

                user_id = auth_response.user.id

                # Step 2: Update profile (trigger created a default row)
                update_resp = (
                    supabase
                    .table("profiles")
                    .update({
                        "first_name":            first,
                        "last_name":             last,
                        "role":                  "student",
                        "approved":              True,
                        "enrollment_number":     enroll_num,
                        "student_id":            enroll_num,
                        "force_password_change": True,
                    })
                    .eq("id", user_id)
                    .execute()
                )

                if not update_resp.data:
                    # Fallback upsert if trigger hasn't fired yet
                    supabase.table("profiles").upsert({
                        "id":                    user_id,
                        "email":                 email,
                        "first_name":            first,
                        "last_name":             last,
                        "role":                  "student",
                        "approved":              True,
                        "enrollment_number":     enroll_num,
                        "student_id":            enroll_num,
                        "force_password_change": True,
                    }).execute()

                # Step 3: Auto-enroll in course if provided
                if course_id and semester_id:
                    supabase.table("enrollments").upsert({
                        "student_id":  user_id,
                        "course_id":   course_id,
                        "semester_id": semester_id,
                        "status":      "active",
                    }).execute()

                created += 1
                logger.info(f"Created student account: {enroll_num} → {email}")

            except Exception as e:
                err_msg = str(e)
                if "already been registered" in err_msg or "already registered" in err_msg:
                    skipped += 1
                else:
                    errors.append(f"{enroll_num}: {err_msg}")
                    logger.exception(f"Failed to create account for {enroll_num}")

        StudentBulkService.clear_cache()
        return created, skipped, errors
