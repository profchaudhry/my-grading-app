"""
Shared Bulk Enrollment UI component.
Used by both admin_console and faculty_console.

allowed_course_ids: set of 7-char course_ids the uploader is allowed to use.
  - Admin: None (all courses allowed)
  - Faculty: only their assigned courses
"""
import streamlit as st
import pandas as pd
from services.student_bulk_service import StudentBulkService
from services.course_service import CourseService
from ui.styles import section_header


def render_bulk_enrollment(
    domain_default: str = "um.ar",
    allowed_course_ids: set | None = None,
    role: str = "admin",
) -> None:

    st.title("📋 Bulk Enrollment")

    # ── Instructions ──────────────────────────────────────────────
    st.markdown("""
    **Excel / CSV column order (required):**

    | # | Column | Example |
    |---|--------|---------|
    | 1 | Enrollment Number | `01-11111-011` |
    | 2 | Full Name | `John Smith` |
    | 3 | Program | `BSc Computer Science` |
    | 4 | Semester | `Fall 2025` |
    | 5 | Course ID | `CS3X7K2` |

    - Students who **don't exist** will have accounts created automatically.
    - Students who **already exist** will have their profile (name, program) updated.
    - All students will be **enrolled** into the course matching the Course ID.
    - Temporary password for new accounts: **ChangeYourPassword**
    """)

    if role == "faculty" and allowed_course_ids is not None:
        st.info(
            f"🔒 As faculty, you can only enroll students into your assigned courses. "
            f"Your Course IDs: **{', '.join(sorted(allowed_course_ids)) or 'None assigned'}**"
        )

    st.divider()

    # ── Domain setting ─────────────────────────────────────────────
    domain = st.text_input(
        "Email Domain for new accounts",
        value=domain_default,
        placeholder="e.g. university.edu",
        help="New student email = enrollment_number@domain"
    )
    if not domain.strip():
        st.warning("Please enter an email domain.")
        return

    st.divider()

    # ── File upload ────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Upload Excel (.xlsx) or CSV file",
        type=["xlsx", "xls", "csv"],
        key=f"bulk_enroll_file_{role}"
    )

    if not uploaded_file:
        return

    # ── Parse ──────────────────────────────────────────────────────
    df, parse_error = StudentBulkService.parse_excel(uploaded_file)
    if parse_error:
        st.error(f"❌ {parse_error}")
        return

    st.success(f"✅ File parsed — **{len(df)} rows** found.")
    st.divider()

    # ── Validate Course IDs ────────────────────────────────────────
    section_header("Step 1 — Course ID Validation",
                   "All Course IDs must match courses in the system before you can proceed.")

    valid_df, invalid_df = StudentBulkService.validate_course_ids(
        df, allowed_course_ids
    )

    # Build the course_map for valid rows (course_id_str → course dict)
    course_map: dict[str, dict] = {}
    unique_valid_cids = valid_df["course_id"].unique().tolist() if not valid_df.empty else []
    for cid in unique_valid_cids:
        course = CourseService.lookup_by_course_id(cid)
        if course:
            course_map[cid] = course

    # Show invalid rows — highlighted in red
    if not invalid_df.empty:
        st.error(
            f"⛔ **{len(invalid_df)} row(s) have invalid Course IDs.** "
            f"Fix them in your file and re-upload before proceeding."
        )

        # Style the invalid rows table
        issue_col   = invalid_df.get("issue", pd.Series(dtype=str))
        display_inv = invalid_df[
            ["enrollment_number", "full_name", "program", "semester", "course_id"]
        ].copy()
        display_inv.columns = [
            "Enrollment Number", "Full Name", "Program", "Semester", "Course ID"
        ]
        display_inv["Issue"] = invalid_df["issue"].values if "issue" in invalid_df.columns \
                                else "Unknown error"

        def _highlight_invalid(row):
            return ["background-color: #fee2e2; color: #991b1b"] * len(row)

        st.dataframe(
            display_inv.style.apply(_highlight_invalid, axis=1),
            use_container_width=True,
            hide_index=True,
        )

        # Hard stop — cannot proceed
        st.warning("⚠️ Fix the highlighted rows in your file and re-upload.")
        return

    # All rows valid
    st.success(f"✅ All **{len(valid_df)} rows** have valid Course IDs.")

    # Show grouped course summary
    grouped = valid_df.groupby("course_id").size().reset_index(name="students")
    grouped["Course Name"] = grouped["course_id"].apply(
        lambda cid: course_map.get(cid, {}).get("name", "—")
    )
    grouped["Semester"] = grouped["course_id"].apply(
        lambda cid: (course_map.get(cid, {}).get("semesters") or {}).get("name", "—")
    )
    grouped.columns = ["Course ID", "Students to Enroll", "Course Name", "Semester"]
    st.dataframe(grouped[["Course ID", "Course Name", "Semester", "Students to Enroll"]],
                 use_container_width=True, hide_index=True)

    st.divider()

    # ── Preview ────────────────────────────────────────────────────
    section_header("Step 2 — Student Preview",
                   "Review all students before accounts are created or updated.")

    existing = StudentBulkService.check_existing_enrollments(
        valid_df["enrollment_number"].tolist()
    )

    preview = valid_df.copy()
    preview["Status"] = preview["enrollment_number"].apply(
        lambda e: "🔄 Update existing" if e in existing else "✅ Create new"
    )
    preview.columns = [
        "Enrollment Number", "Full Name", "Program", "Semester", "Course ID", "Status"
    ]

    # Colour-code: green = new, blue = update
    def _highlight_status(row):
        if "Create" in str(row["Status"]):
            return ["background-color: #dcfce7"] * len(row)
        return ["background-color: #dbeafe"] * len(row)

    st.dataframe(
        preview.style.apply(_highlight_status, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    new_count    = len(preview[preview["Status"].str.contains("Create")])
    update_count = len(preview[preview["Status"].str.contains("Update")])

    col1, col2 = st.columns(2)
    col1.metric("🟢 New accounts to create", new_count)
    col2.metric("🔵 Existing profiles to update", update_count)

    st.divider()

    # ── Course ID confirmation ─────────────────────────────────────
    section_header("Step 3 — Confirm Course IDs",
                   "Verify the Course IDs before processing.")

    confirm_ids = ", ".join(sorted(valid_df["course_id"].unique().tolist()))
    st.markdown(f"**Course IDs in this upload:** `{confirm_ids}`")

    confirmed = st.checkbox(
        f"✅ I have verified the Course ID(s) above are correct and want to proceed.",
        key=f"confirm_cids_{role}"
    )

    if not confirmed:
        st.info("Check the box above to unlock the upload button.")
        return

    st.divider()

    # ── Process ────────────────────────────────────────────────────
    if st.button(
        f"🚀 Process {len(valid_df)} Student(s)",
        type="primary",
        use_container_width=True,
        key=f"process_bulk_{role}"
    ):
        with st.spinner(f"Processing {len(valid_df)} students..."):
            created, updated_count, skipped, errors = (
                StudentBulkService.create_or_update_student_accounts(
                    valid_df, domain.strip(), course_map
                )
            )

        st.divider()
        section_header("Results")

        r1, r2, r3 = st.columns(3)
        if created:
            r1.success(f"✅ {created} new account(s) created")
        if updated_count:
            r2.info(f"🔄 {updated_count} profile(s) updated")
        if skipped:
            r3.warning(f"⏭️ {skipped} skipped (auth conflict)")

        if errors:
            st.error(f"❌ {len(errors)} error(s) encountered:")
            for err in errors:
                st.caption(f"• {err}")

        if not errors:
            st.balloons()
