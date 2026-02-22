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
st.sidebar.write(f"Logged in as: **{profile.get('first_name', 'User')}** ({role})")

# Force password change logic
enforce_password_change()

# ================= HELPER FUNCTIONS =================
def fetch_data(table, select_query="*", filters=None):
    """Helper to safely fetch data from Supabase"""
    try:
        query = supabase.table(table).select(select_query)
        if filters:
            for col, val in filters.items():
                if isinstance(val, list):
                    query = query.in_(col, val)
                else:
                    query = query.eq(col, val)
        res = query.execute()
        return res.data
    except Exception as e:
        st.error(f"Database Error in {table}: {e}")
        return []

# ==================================================
# ====================== ADMIN =====================
# ==================================================
if role == "admin":
    page = st.sidebar.radio(
        "Admin Menu",
        ["Dashboard", "Create Course", "Assign Course", "Enroll Student", "Approve Faculty", "View All Profiles"]
    )

    if page == "Dashboard":
        st.title("Admin Dashboard")
        st.write("System Overview and Statistics.")

    elif page == "Create Course":
        st.title("Create New Course")
        with st.form("create_course", clear_on_submit=True):
            col1, col2 = st.columns(2)
            code = col1.text_input("Course Code (e.g., CS101)")
            title = col2.text_input("Course Title")
            credits = col1.number_input("Credit Hours", 1, 6, 3)
            semester = col2.text_input("Semester")
            
            if st.form_submit_button("Create"):
                if code and title:
                    supabase.table("courses").insert({
                        "course_code": code, "course_title": title,
                        "credit_hours": credits, "semester": semester
                    }).execute()
                    st.success(f"Course {code} created successfully!")
                else:
                    st.error("Please fill in required fields.")

    elif page == "Assign Course":
        st.title("Assign Faculty to Course")
        # Fixed query: removed potentially missing columns for testing
        faculty = fetch_data("profiles", "id, email", {"role": ["faculty", "faculty_pro"]})
        courses = fetch_data("courses")

        if faculty and courses:
            f_map = {f['email']: f["id"] for f in faculty}
            c_map = {f"{c['course_code']} - {c['course_title']}": c["id"] for c in courses}
            
            sel_f = st.selectbox("Select Faculty", f_map.keys())
            sel_c = st.selectbox("Select Course", c_map.keys())

            if st.button("Assign"):
                try:
                    supabase.table("faculty_courses").insert({
                        "faculty_id": f_map[sel_f], 
                        "course_id": c_map[sel_c]
                    }).execute()
                    st.success("Assigned Successfully")
                except Exception as e:
                    st.warning("This assignment might already exist.")
        else:
            st.warning("Ensure faculty and courses exist.")

    elif page == "Enroll Student":
        st.title("Enroll Student")
        students = fetch_data("profiles", "id, email", {"role": "student"})
        courses = fetch_data("courses")

        if students and courses:
            s_map = {s["email"]: s["id"] for s in students}
            c_map = {f"{c['course_code']} - {c['course_title']}": c["id"] for c in courses}
            
            sel_s = st.selectbox("Select Student", s_map.keys())
            sel_c = st.selectbox("Select Course", c_map.keys())

            if st.button("Enroll"):
                try:
                    supabase.table("student_enrollments").insert({
                        "student_id": s_map[sel_s], "course_id": c_map[sel_c]
                    }).execute()
                    st.success("Student Enrolled!")
                except:
                    st.warning("Student already enrolled.")

    elif page == "Approve Faculty":
        st.title("Approve Faculty")
        pending = fetch_data("profiles", "*", {"role": "pending_faculty"})
        if not pending:
            st.info("No pending faculty.")
        else:
            for f in pending:
                col1, col2 = st.columns([3, 1])
                col1.write(f"{f['email']}")
                if col2.button("Approve", key=f["id"]):
                    supabase.table("profiles").update({"role": "faculty"}).eq("id", f["id"]).execute()
                    st.rerun()

    elif page == "View All Profiles":
        st.title("All User Profiles")
        users = fetch_data("profiles")
        st.dataframe(users)

# ==================================================
# ====================== FACULTY ===================
# ==================================================
elif role in ["faculty", "faculty_pro"]:
    page = st.sidebar.radio("Faculty Menu", ["Dashboard", "My Courses", "Create Assessment", "Enter Grades"])

    # Pre-fetch assigned courses for the faculty
    assignments = supabase.table("faculty_courses").select("course_id, courses(*)").eq("faculty_id", profile["id"]).execute()
    assigned_courses = assignments.data if assignments.data else []

    if page == "My Courses":
        st.title("My Assigned Courses")
        if assigned_courses:
            display_data = [item['courses'] for item in assigned_courses]
            st.table(display_data)
        else:
            st.info("No courses assigned.")

    elif page == "Create Assessment":
        st.title("Create Assessment")
        if assigned_courses:
            c_map = {f"{c['courses']['course_code']}": c['course_id'] for c in assigned_courses}
            sel_c = st.selectbox("Course", list(c_map.keys()))
            
            with st.form("assessment_form"):
                title = st.text_input("Assessment Title")
                a_type = st.selectbox("Type", ["Quiz", "Assignment", "Mid", "Final"])
                max_m = st.number_input("Max Marks", 1, 100, 10)
                weight = st.number_input("Weightage (%)", 0, 100, 10)
                
                if st.form_submit_button("Create"):
                    supabase.table("assessments").insert({
                        "course_id": c_map[sel_c], "title": title,
                        "type": a_type, "max_marks": max_m, "weightage": weight
                    }).execute()
                    st.success("Assessment Created!")
        else:
            st.error("You need assigned courses first.")

    elif page == "Enter Grades":
        st.title("Enter Grades")
        if assigned_courses:
            c_map = {f"{c['courses']['course_code']}": c['course_id'] for c in assigned_courses}
            sel_c = st.selectbox("Select Course", list(c_map.keys()))
            course_id = c_map[sel_c]
            
            # Fetch context for grading
            assessments = fetch_data("assessments", "*", {"course_id": course_id})
            enrollments = supabase.table("student_enrollments").select("profiles(id, email)").eq("course_id", course_id).execute()
            students = enrollments.data if enrollments.data else []

            if assessments and students:
                a_map = {a["title"]: a["id"] for a in assessments}
                s_map = {s['profiles']['email']: s['profiles']['id'] for s in students}
                
                sel_a = st.selectbox("Select Assessment", list(a_map.keys()))
                sel_s = st.selectbox("Select Student", list(s_map.keys()))
                
                # Dynamic max marks check
                current_max = next(a['max_marks'] for a in assessments if a['id'] == a_map[sel_a])
                marks = st.number_input("Marks Obtained", 0.0, float(current_max))
                
                if st.button("Submit Grade"):
                    supabase.table("grades").upsert({
                        "assessment_id": a_map[sel_a],
                        "student_id": s_map[sel_s],
                        "marks_obtained": marks
                    }).execute()
                    st.success("Grade Saved!")
            else:
                st.warning("Ensure assessments are created and students are enrolled.")

# ==================================================
# ====================== STUDENT ===================
# ==================================================
elif role == "student":
    st.title("My Academic Records")
    
    grades = supabase.table("grades").select(
        "marks_obtained, assessments(title, max_marks, courses(course_title))"
    ).eq("student_id", profile["id"]).execute()
    
    if grades.data:
        report = []
        for g in grades.data:
            report.append({
                "Course": g['assessments']['courses']['course_title'],
                "Assessment": g['assessments']['title'],
                "Score": f"{g['marks_obtained']} / {g['assessments']['max_marks']}"
            })
        st.table(report)
    else:
        st.info("No grades available yet.")

logout()
