import logging
import pandas as pd
import streamlit as st
from services.supabase_client import supabase
from services.base_service import BaseService

logger = logging.getLogger("sylemax.student_bulk_service")

TEMP_PASSWORD = "ChangeYourPassword"

# Expected columns (flexible matching)
COL_ENROLLMENT = "enrollment_number"
COL_FULL_NAME  = "full_name"
COL_PROGRAM    = "program"
COL_SEMESTER   = "semester"
COL_COURSE_ID  = "course_id"


class StudentBulkService(BaseService):

    @staticmethod
    def parse_excel(file) -> tuple[pd.DataFrame | None, str]:
        """
        Parses uploaded Excel/CSV.
        Expected columns (order matters, flexible names):
          1. Enrollment Number
          2. Full Name
          3. Program
          4. Semester
          5. Course ID
        Returns (dataframe, error_message).
        """
        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            df.columns = [str(c).strip() for c in df.columns]

            # Flexible column name matching
            col_map = {}
            for col in df.columns:
                key = col.lower().replace(" ", "").replace("_", "").replace("-", "")
                if key in ("enrollmentnumber", "enrollmentno", "enrollmentnum",
                           "enrollment", "rollno", "rollnumber", "regno",
                           "registrationnumber", "studentid", "enrollmentid"):
                    col_map[COL_ENROLLMENT] = col
                elif key in ("fullname", "name", "studentname"):
                    col_map[COL_FULL_NAME] = col
                elif key in ("program", "programme", "degree", "programdegree"):
                    col_map[COL_PROGRAM] = col
                elif key in ("semester", "term", "session"):
                    col_map[COL_SEMESTER] = col
                elif key in ("courseid", "course", "coursecode", "cid"):
                    col_map[COL_COURSE_ID] = col

            missing = []
            for req in [COL_ENROLLMENT, COL_FULL_NAME, COL_PROGRAM,
                        COL_SEMESTER, COL_COURSE_ID]:
                if req not in col_map:
                    missing.append(req.replace("_", " ").title())
            if missing:
                return None, (
                    f"Missing column(s): {', '.join(missing)}. "
                    f"Expected: Enrollment Number, Full Name, Program, Semester, Course ID"
                )

            df = df.rename(columns={v: k for k, v in col_map.items()})
            df = df[[COL_ENROLLMENT, COL_FULL_NAME, COL_PROGRAM,
                     COL_SEMESTER, COL_COURSE_ID]].copy()

            # Clean
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()

            df = df[df[COL_ENROLLMENT].notna() & (df[COL_ENROLLMENT] != "") &
                    (df[COL_ENROLLMENT] != "nan")]
            df = df[df[COL_FULL_NAME].notna()  & (df[COL_FULL_NAME] != "") &
                    (df[COL_FULL_NAME] != "nan")]
            df = df.drop_duplicates(subset=[COL_ENROLLMENT])

            if df.empty:
                return None, "File is empty or has no valid rows."

            return df, ""

        except Exception as e:
            logger.exception("Failed to parse file.")
            return None, f"Failed to read file: {str(e)}"

    @staticmethod
    def validate_course_ids(
        df: pd.DataFrame,
        allowed_course_ids: set[str] | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Validates all course_ids in the dataframe against the database
        (and optionally against a set of allowed IDs for faculty).

        Returns (valid_df, invalid_df).
        invalid_df has an extra 'issue' column describing the problem.
        """
        from services.course_service import CourseService

        unique_cids = df[COL_COURSE_ID].str.upper().unique().tolist()

        # Batch lookup
        course_map = {}
        for cid in unique_cids:
            course = CourseService.lookup_by_course_id(cid)
            if course:
                course_map[cid] = course

        df = df.copy()
        df[COL_COURSE_ID] = df[COL_COURSE_ID].str.upper()

        valid_rows   = []
        invalid_rows = []

        for _, row in df.iterrows():
            cid = row[COL_COURSE_ID]
            if cid not in course_map:
                row = row.copy()
                row["issue"] = f"Course ID '{cid}' not found in system"
                invalid_rows.append(row)
            elif allowed_course_ids is not None and cid not in allowed_course_ids:
                row = row.copy()
                row["issue"] = f"Course ID '{cid}' not assigned to you"
                invalid_rows.append(row)
            else:
                valid_rows.append(row)

        valid_df   = pd.DataFrame(valid_rows)   if valid_rows   else pd.DataFrame(columns=df.columns)
        invalid_df = pd.DataFrame(invalid_rows) if invalid_rows else pd.DataFrame()

        return valid_df, invalid_df

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
    def build_email(enrollment_number: str, domain: str) -> str:
        domain = domain.strip().lstrip("@")
        safe   = enrollment_number.strip().replace(" ", ".")
        return f"{safe}@{domain}"

    @staticmethod
    def get_profile_by_enrollment(enrollment_number: str) -> dict | None:
        try:
            resp = (
                supabase
                .table("profiles")
                .select("*")
                .eq("enrollment_number", enrollment_number)
                .execute()
            )
            return resp.data[0] if resp.data else None
        except Exception:
            return None

    @staticmethod
    def create_or_update_student_accounts(
        df: pd.DataFrame,
        domain: str,
        course_map: dict,          # course_id_str → full course dict
    ) -> tuple[int, int, int, list[str]]:
        """
        For each row:
          - If student doesn't exist → create auth account + profile
          - If student exists → update full_name, program fields
          - Enroll into the course specified in the row's course_id column
        Returns (created, updated, skipped, errors).
        """
        from services.course_service import CourseService

        created, updated, skipped, errors = 0, 0, 0, []

        existing_map: dict[str, dict] = {}
        for enum in df[COL_ENROLLMENT].tolist():
            p = StudentBulkService.get_profile_by_enrollment(enum)
            if p:
                existing_map[enum] = p

        for _, row in df.iterrows():
            enroll_num = str(row[COL_ENROLLMENT]).strip()
            full_name  = str(row[COL_FULL_NAME]).strip()
            program    = str(row[COL_PROGRAM]).strip()
            cid_str    = str(row[COL_COURSE_ID]).strip().upper()

            course     = course_map.get(cid_str)
            if not course:
                errors.append(f"{enroll_num}: Course ID '{cid_str}' not resolved.")
                continue

            course_uuid    = course["id"]
            semester_uuid  = course.get("semester_id")

            try:
                if enroll_num in existing_map:
                    # ── Update existing profile ──
                    profile = existing_map[enroll_num]
                    uid     = profile["id"]
                    supabase.table("profiles").update({
                        "full_name": full_name,
                        "program":   program,
                    }).eq("id", uid).execute()

                    # Enroll
                    supabase.table("enrollments").upsert({
                        "student_id":  uid,
                        "course_id":   course_uuid,
                        "semester_id": semester_uuid,
                        "status":      "active",
                    }).execute()
                    updated += 1

                else:
                    # ── Create new account ──
                    email = StudentBulkService.build_email(enroll_num, domain)

                    auth_resp = supabase.auth.admin.create_user({
                        "email":         email,
                        "password":      TEMP_PASSWORD,
                        "email_confirm": True,
                    })
                    if not auth_resp or not auth_resp.user:
                        errors.append(f"{enroll_num}: Auth creation failed.")
                        continue

                    uid = auth_resp.user.id

                    # Update trigger-created profile
                    update_resp = supabase.table("profiles").update({
                        "full_name":             full_name,
                        "first_name":            full_name.split(" ", 1)[0],
                        "last_name":             full_name.split(" ", 1)[1] if " " in full_name else "",
                        "role":                  "student",
                        "approved":              True,
                        "enrollment_number":     enroll_num,
                        "student_id":            enroll_num,
                        "program":               program,
                        "force_password_change": True,
                    }).eq("id", uid).execute()

                    if not update_resp.data:
                        supabase.table("profiles").upsert({
                            "id":                    uid,
                            "email":                 email,
                            "full_name":             full_name,
                            "first_name":            full_name.split(" ", 1)[0],
                            "last_name":             full_name.split(" ", 1)[1] if " " in full_name else "",
                            "role":                  "student",
                            "approved":              True,
                            "enrollment_number":     enroll_num,
                            "student_id":            enroll_num,
                            "program":               program,
                            "force_password_change": True,
                        }).execute()

                    # Enroll
                    supabase.table("enrollments").upsert({
                        "student_id":  uid,
                        "course_id":   course_uuid,
                        "semester_id": semester_uuid,
                        "status":      "active",
                    }).execute()

                    created += 1
                    logger.info(f"Created student: {enroll_num} → {email}")

            except Exception as e:
                err = str(e)
                if "already been registered" in err or "already registered" in err:
                    skipped += 1
                else:
                    errors.append(f"{enroll_num}: {err}")
                    logger.exception(f"Failed for {enroll_num}")

        StudentBulkService.clear_cache()
        return created, updated, skipped, errors
