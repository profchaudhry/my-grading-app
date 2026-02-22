import streamlit as st
from utils.auth import login, logout, enforce_password_change
from utils.db import supabase

st.set_page_config(page_title="UCS System", layout="wide")

# ================= SESSION CHECK =================
if "user" not in st.session_state:
    login()
    st.stop()

profile = st.session_state.profile
role = profile["role"]

st.sidebar.title("UCS Navigation")
st.sidebar.write(f"Logged in as: {role}")

enforce_password_change()

# ==================================================
# ====================== ADMIN =====================
# ==================================================
if role == "admin":

    page = st.sidebar.radio(
        "Admin Menu",
        [
            "Dashboard",
            "Create Course",
            "Assign Course",
            "Enroll Student",
            "Approve Faculty",
            "View All Profiles"
        ]
    )

    # ---------------- Dashboard ----------------
    if page == "Dashboard":
        st.title("Admin Dashboard")
        st.write("System Overview")

    # ---------------- Create Course ----------------
    if page == "Create Course":
        st.title("Create Course")

        with st.form("create_course"):
            code = st.text_input("Course Code")
            title = st.text_input("Course Title")
            credits = st.number_input("Credit Hours", 1, 6)
            semester = st.text_input("Semester")

            submitted = st.form_submit_button("Create")

            if submitted:
                supabase.table("courses").insert({
                    "course_code": code,
                    "course_title": title,
                    "credit_hours": credits,
                    "semester": semester
                }).execute()

                st.success("Course Created")
                st.rerun()

    # ---------------- Assign Course ----------------
    if page == "Assign Course":

        st.title("Assign Course to Faculty")

        faculty = supabase.table("profiles") \
            .select("id,email") \
            .in_("role", ["faculty", "faculty_pro"]) \
            .execute()

        courses = supabase.table("courses").select("*").execute()

        if faculty.data and courses.data:

            faculty_dict = {f["email"]: f["id"] for f in faculty.data}
            course_dict = {
                f'{c["course_code"]} - {c["course_title"]}': c["id"]
                for c in courses.data
            }

            selected_faculty = st.selectbox("Select Faculty", list(faculty_dict.keys()))
            selected_course = st.selectbox("Select Course", list(course_dict.keys()))

            if st.button("Assign"):
                supabase.table("faculty_courses").insert({
                    "faculty_id": faculty_dict[selected_faculty],
                    "course_id": course_dict[selected_course]
                }).execute()

                st.success("Assigned")
                st.rerun()

    # ---------------- Enroll Student ----------------
    if page == "Enroll Student":

        st.title("Enroll Student in Course")

        students = supabase.table("profiles") \
            .select("id,email") \
            .eq("role", "student") \
            .execute()

        courses = supabase.table("courses").select("*").execute()

        if students.data and courses.data:

            student_dict = {s["email"]: s["id"] for s in students.data}
            course_dict = {
                f'{c["course_code"]} - {c["course_title"]}': c["id"]
                for c in courses.data
            }

            selected_student = st.selectbox("Select Student", list(student_dict.keys()))
            selected_course = st.selectbox("Select Course", list(course_dict.keys()))

            if st.button("Enroll"):
                supabase.table("student_enrollments").insert({
                    "student_id": student_dict[selected_student],
                    "course_id": course_dict[selected_course]
                }).execute()

                st.success("Student Enrolled")
                st.rerun()

    # ---------------- Approve Faculty ----------------
    if page == "Approve Faculty":

        st.title("Approve Faculty")

        pending = supabase.table("profiles") \
            .select("*") \
            .eq("role", "pending_faculty") \
            .execute()

        if not pending.data:
            st.success("No pending faculty.")
        else:
            for faculty in pending.data:
                col1, col2 = st.columns([4, 1])
                col1.write(faculty["email"])

                if col2.button("Approve", key=faculty["id"]):
                    supabase.table("profiles").update({
                        "role": "faculty"
                    }).eq("id", faculty["id"]).execute()

                    st.success("Approved")
                    st.rerun()

    # ---------------- View Profiles ----------------
    if page == "View All Profiles":
        users = supabase.table("profiles").select("*").execute()
        st.dataframe(users.data)


# ==================================================
# ====================== FACULTY ===================
# ==================================================
elif role in ["faculty", "faculty_pro"]:

    page = st.sidebar.radio(
        "Faculty Menu",
        [
            "Dashboard",
            "My Courses",
            "Create Assessment",
            "Enter Grades"
        ]
    )

    if page == "Dashboard":
        st.title("Faculty Dashboard")

    # ---------------- My Courses ----------------
    if page == "My Courses":

        assignments = supabase.table("faculty_courses") \
            .select("course_id") \
            .eq("faculty_id", profile["id"]) \
            .execute()

        if assignments.data:
            course_ids = [a["course_id"] for a in assignments.data]

            courses = supabase.table("courses") \
                .select("*") \
                .in_("id", course_ids) \
                .execute()

            st.dataframe(courses.data)
        else:
            st.info("No courses assigned.")

    # ---------------- Create Assessment ----------------
    if page == "Create Assessment":

        assignments = supabase.table("faculty_courses") \
            .select("course_id") \
            .eq("faculty_id", profile["id"]) \
            .execute()

        if assignments.data:

            course_ids = [a["course_id"] for a in assignments.data]

            courses = supabase.table("courses") \
                .select("*") \
                .in_("id", course_ids) \
                .execute()

            course_dict = {
                f'{c["course_code"]} - {c["course_title"]}': c["id"]
                for c in courses.data
            }

            selected_course = st.selectbox("Select Course", list(course_dict.keys()))

            title = st.text_input("Assessment Title")
            type_ = st.selectbox("Type", ["Quiz", "Assignment", "Mid", "Final"])
            max_marks = st.number_input("Max Marks", min_value=1)
            weight = st.number_input("Weightage (%)", min_value=0.0)

            if st.button("Create"):
                supabase.table("assessments").insert({
                    "course_id": course_dict[selected_course],
                    "title": title,
                    "type": type_,
                    "max_marks": max_marks,
                    "weightage": weight
                }).execute()

                st.success("Assessment Created")
                st.rerun()

# ==================================================
# ====================== STUDENT ===================
# ==================================================
elif role == "student":

    st.title("My Grades")
    st.write("Grade viewing working here (as before).")

logout()
