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
# ====================== FACULTY ===================
# ==================================================
if role in ["faculty", "faculty_pro"]:

    page = st.sidebar.radio(
        "Faculty Menu",
        [
            "Dashboard",
            "My Courses",
            "Create Assessment",
            "Enter Grades"
        ]
    )

    # ---------------- MY COURSES ----------------
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

    # ---------------- CREATE ASSESSMENT ----------------
    if page == "Create Assessment":

        st.title("Create Assessment")

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

    # ---------------- ENTER GRADES ----------------
    if page == "Enter Grades":

        st.title("Enter Grades")

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

            assessments = supabase.table("assessments") \
                .select("*") \
                .eq("course_id", course_dict[selected_course]) \
                .execute()

            if assessments.data:

                assess_dict = {
                    f'{a["title"]} ({a["type"]})': a["id"]
                    for a in assessments.data
                }

                selected_assessment = st.selectbox("Select Assessment", list(assess_dict.keys()))

                enrollments = supabase.table("student_enrollments") \
                    .select("student_id") \
                    .eq("course_id", course_dict[selected_course]) \
                    .execute()

                if enrollments.data:

                    student_ids = [e["student_id"] for e in enrollments.data]

                    students = supabase.table("profiles") \
                        .select("id,email") \
                        .in_("id", student_ids) \
                        .execute()

                    for student in students.data:
                        marks = st.number_input(
                            f'Marks for {student["email"]}',
                            min_value=0.0,
                            key=student["id"]
                        )

                        if st.button(f"Save {student['email']}", key=f"btn_{student['id']}"):
                            supabase.table("grades").insert({
                                "assessment_id": assess_dict[selected_assessment],
                                "student_id": student["id"],
                                "marks_obtained": marks
                            }).execute()

                            st.success("Saved")

                else:
                    st.info("No students enrolled.")

            else:
                st.info("No assessments created.")


# ==================================================
# ====================== STUDENT ===================
# ==================================================
elif role == "student":

    st.title("My Grades")

    enrollments = supabase.table("student_enrollments") \
        .select("course_id") \
        .eq("student_id", profile["id"]) \
        .execute()

    if enrollments.data:

        course_ids = [e["course_id"] for e in enrollments.data]

        courses = supabase.table("courses") \
            .select("*") \
            .in_("id", course_ids) \
            .execute()

        for course in courses.data:

            st.subheader(f'{course["course_code"]} - {course["course_title"]}')

            assessments = supabase.table("assessments") \
                .select("*") \
                .eq("course_id", course["id"]) \
                .execute()

            for assess in assessments.data:

                grade = supabase.table("grades") \
                    .select("marks_obtained") \
                    .eq("assessment_id", assess["id"]) \
                    .eq("student_id", profile["id"]) \
                    .execute()

                if grade.data:
                    st.write(f'{assess["title"]}: {grade.data[0]["marks_obtained"]}')
                else:
                    st.write(f'{assess["title"]}: Not graded')

    else:
        st.info("Not enrolled in any course.")


logout()
