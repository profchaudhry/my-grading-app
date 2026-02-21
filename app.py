import streamlit as st
import pandas as pd
from supabase import create_client

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Sylemas", layout="wide")
st.title("🎓 Sylemas — Syndicate Learning Management System")

# -----------------------------
# SUPABASE CONNECTION
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# DATABASE FUNCTIONS
# -----------------------------

def load_students():
    response = supabase.table("students").select("*").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def upsert_student(data):
    supabase.table("students").upsert(data).execute()

def update_student(enrollment, data):
    supabase.table("students").update(data).eq("enrollment", enrollment).execute()

def update_group(syndicate_name, data):
    supabase.table("students").update(data).eq("syndicate_name", syndicate_name).execute()

# -----------------------------
# SIDEBAR NAVIGATION
# -----------------------------
menu = [
    "1. Upload Roster (Admin)",
    "2. Student Registration",
    "3. Faculty Grading",
    "4. Export Data"
]

choice = st.sidebar.radio("Navigation", menu)

# =============================
# MODULE 1 — UPLOAD ROSTER
# =============================
if choice == "1. Upload Roster (Admin)":

    st.header("Admin: Upload Class Roster")

    col1, col2 = st.columns(2)

    with col1:
        semester = st.text_input("Semester (e.g., Spring 2026)")

    with col2:
        course = st.text_input("Course Name")

    file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

    if file and st.button("Process Roster"):

        new_df = pd.read_excel(file)

        if "Enrollment" not in new_df.columns or "Name" not in new_df.columns:
            st.error("Excel must contain 'Enrollment' and 'Name' columns.")
        else:
            for _, row in new_df.iterrows():
                upsert_student({
                    "enrollment": str(row["Enrollment"]),
                    "name": row["Name"],
                    "course": course,
                    "semester": semester
                })

            st.success("Roster saved permanently in database!")

# =============================
# MODULE 2 — STUDENT REGISTRATION
# =============================
elif choice == "2. Student Registration":

    st.header("Student: Join a Syndicate")

    db = load_students()

    if db.empty:
        st.warning("No roster found. Please ask Admin to upload the class list.")
    else:
        student_id = st.selectbox("Select your Enrollment Number", db["enrollment"].unique())

        student_record = db[db["enrollment"] == student_id].iloc[0]

        with st.form("student_form"):

            email = st.text_input("Email", value=student_record.get("email", ""))
            phone = st.text_input("Phone", value=student_record.get("phone", ""))
            syndicate = st.text_input("Syndicate Name", value=student_record.get("syndicate_name", "Unassigned"))
            is_lead = st.checkbox("I am Syndicate Lead", value=student_record.get("is_lead", False))

            if st.form_submit_button("Submit"):

                update_student(student_id, {
                    "email": email,
                    "phone": phone,
                    "syndicate_name": syndicate,
                    "is_lead": is_lead
                })

                st.success("Details updated successfully!")
                st.rerun()

# =============================
# MODULE 3 — FACULTY GRADING
# =============================
elif choice == "3. Faculty Grading":

    st.header("Faculty: Grading Dashboard")

    db = load_students()

    if db.empty:
        st.warning("No students found.")
    else:
        groups = db["syndicate_name"].dropna().unique()

        selected_group = st.selectbox("Select Syndicate", groups)

        if selected_group and selected_group != "Unassigned":

            st.subheader(f"Group Grading — {selected_group}")

            group_grade = st.number_input("Set Group Grade", 0, 100)

            if st.button("Apply Group Grade"):
                update_group(selected_group, {"syndicate_grade": group_grade})
                st.success("Group grade applied!")
                st.rerun()

            st.subheader("Individual Adjustments")

            members = db[db["syndicate_name"] == selected_group]

            for _, row in members.iterrows():

                col1, col2 = st.columns([3,1])
                col1.write(f"{row['name']} ({row['enrollment']})")

                new_grade = col2.number_input(
                    "Individual Grade",
                    0,
                    100,
                    value=int(row.get("individual_grade", 0)),
                    key=f"grade_{row['enrollment']}"
                )

                update_student(row["enrollment"], {
                    "individual_grade": new_grade
                })

# =============================
# MODULE 4 — EXPORT
# =============================
elif choice == "4. Export Data":

    st.header("Download Student Data")

    db = load_students()

    if db.empty:
        st.warning("No data available.")
    else:
        st.dataframe(db)

        csv = db.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="sylemas_export.csv",
            mime="text/csv"
        )
