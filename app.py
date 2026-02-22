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
            "Approve Faculty"
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
            credits = st.number_input("Credit Hours", min_value=1, max_value=6)
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

        courses = supabase.table("courses") \
            .select("*") \
            .execute()

        if faculty.data and courses.data:

            faculty_dict = {f["email"]: f["id"] for f in faculty.data}
            course_dict = {
                f'{c["course_code"]} - {c["course_title"]}': c["id"]
                for c in courses.data
            }

            selected_faculty = st.selectbox("Select Faculty", list(faculty_dict.keys()))
            selected_course = st.selectbox("Select Course", list(course_dict.keys()))

            if st.button("Assign Course"):
                supabase.table("faculty_courses").insert({
                    "faculty_id": faculty_dict[selected_faculty],
                    "course_id": course_dict[selected_course]
                }).execute()

                st.success("Course Assigned")
                st.rerun()

        else:
            st.warning("No faculty or courses available.")

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


# ==================================================
# ==================== FACULTY =====================
# ==================================================
elif role in ["faculty", "faculty_pro"]:

    page = st.sidebar.radio(
        "Faculty Menu",
        [
            "Dashboard",
            "My Courses"
        ]
    )

    # ---------------- Dashboard ----------------
    if page == "Dashboard":
        st.title("Faculty Dashboard")
        st.write("Welcome.")

    # ---------------- My Courses ----------------
    if page == "My Courses":

        st.title("My Assigned Courses")

        assignments = supabase.table("faculty_courses") \
            .select("course_id") \
            .eq("faculty_id", profile["id"]) \
            .execute()

        if not assignments.data:
            st.info("No courses assigned.")
        else:
            course_ids = [a["course_id"] for a in assignments.data]

            courses = supabase.table("courses") \
                .select("*") \
                .in_("id", course_ids) \
                .execute()

            st.dataframe(courses.data)


# ==================================================
# ==================== STUDENT =====================
# ==================================================
elif role == "student":

    st.title("Student Dashboard")
    st.write("Student features coming soon.")


# ==================================================
# ===================== LOGOUT =====================
# ==================================================
logout()
