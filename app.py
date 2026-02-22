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

# Force password change if required
enforce_password_change()

# ================= HELPER FUNCTIONS =================
def get_faculty_courses(fid):
    res = supabase.table("faculty_courses").select("course_id, courses(*)").eq("faculty_id", fid).execute()
    return res.data

# ==================================================
# ====================== ADMIN =====================
# ==================================================
if role == "admin":
    page = st.sidebar.radio("Admin Menu", ["Dashboard", "Create Course", "Assign Course", "Enroll Student", "Approve Faculty", "View All Profiles"])

    if page == "Dashboard":
        st.title("Admin Dashboard")
        # Add quick stats in 1.8
        st.write("Welcome to the system control center.")

    elif page == "Create Course":
        st.title("Create New Course")
        with st.form("create_course", clear_on_submit=True):
            col1, col2 = st.columns(2)
            code = col1.text_input("Course Code (e.g., CS101)")
            title = col2.text_input("Course Title")
            credits = col1.number_input("Credit Hours", 1, 6, 3)
            semester = col2.text_input("Semester (e.g., Fall 2025)")
            
            if st.form_submit_button("Create Course"):
                if code and title:
                    supabase.table("courses").insert({
                        "course_code": code, "course_title": title,
                        "credit_hours": credits, "semester": semester
                    }).execute()
                    st.success(f"Course {code} created!")
                else:
                    st.error("Please fill in all fields.")

    elif page == "Assign Course":
        st.title("Assign Faculty to Course")
        faculty = supabase.table("profiles").select("id, email, last_name").in_("role", ["faculty", "faculty_pro"]).execute()
        courses = supabase.table("courses").select("*").execute()

        if faculty.data and courses.data:
            f_map = {f"{f['last_name']} ({f['email']})": f["id"] for f in faculty.data}
            c_map = {f"{c['course_code']} - {c['course_title']}": c["id"] for c in courses.data}
            
            sel_f = st.selectbox("Select Faculty", f_map.keys())
            sel_c = st.selectbox("Select Course", c_map.keys())

            if st.button("Assign"):
                # Unique constraint in DB (from 1.7 fix) handles the logic; Python check is for UX
                res = supabase.table("faculty_courses").insert({"faculty_id": f_map[sel_f], "course_id": c_map[sel_c]}).execute()
                st.success("Assignment successful!")
        else:
            st.warning("Ensure faculty and courses exist.")

    elif page == "Enroll Student":
        st.title("Student Enrollment")
        students = supabase.table("profiles").select("id, email").eq("role", "student").execute()
        courses = supabase.table("courses").select("*").execute()

        if students.data and courses.data:
            s_map = {s["email"]: s["id"] for s in students.data}
            c_map = {f"{c['course_code']} - {c['course_title']}": c["id"] for c in courses.data}
            
            sel_s = st.selectbox("Select Student", s_map.keys())
            sel_c = st.selectbox("Select Course", c_map.keys())

            if st.button("Enroll"):
                supabase.table("student_enrollments").insert({"student_id": s_map[sel_s], "course_id": c_map[sel_c]}).execute()
                st.success("Student Enrolled!")

    elif page == "Approve Faculty":
        st.title("Pending Approvals")
        pending = supabase.table("profiles").select("*").eq("role", "pending_faculty").execute()
        if not pending.data:
            st.info("No faculty awaiting approval.")
        else:
            for f in pending.data:
                col1, col2 = st.columns([3, 1])
                col1.write(f"{f['first_name']} {f['last_name']} ({f['email']})")
                if col2.button("Approve", key=f["id"]):
                    supabase.table("profiles").update({"role": "faculty"}).eq("id", f["id"]).execute()
                    st.rerun()

    elif page == "View All Profiles":
        st.title("System Users")
        users = supabase.table("profiles").select("*").execute()
        st.dataframe(users.data, use_container_width=True)

# ==================================================
# ====================== FACULTY ===================
# ==================================================
elif role in ["faculty", "faculty_pro"]:
    page = st.sidebar.radio("Faculty Menu", ["Dashboard", "My Courses", "Create Assessment", "Enter Grades"])

    if page == "My Courses":
        st.title("My Assigned Courses")
        data = get_faculty_courses(profile["id"])
        if data:
            # Flatten data for display
            display_data = [item['courses'] for item in data]
            st.table(display_data)
        else:
            st.info("You haven't been assigned any courses yet.")

    elif page == "Create Assessment":
        st.title("New Assessment")
        courses = get_faculty_courses(profile["id"])
        if courses:
            c_map = {f"{c['courses']['course_code']}": c['course_id'] for c in courses}
            sel_c = st.selectbox("Course", c_map.keys())
            
            with st.form("assessment_form"):
                title = st.text_input("Assessment Name (e.g., Quiz 1)")
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
            st.error("Assign courses first.")

    elif page == "Enter Grades":
        st.title("Grade Entry")
        courses = get_faculty_courses(profile["id"])
        if courses:
            c_map = {f"{c['courses']['course_code']}": c['course_id'] for c in courses}
            sel_c = st.selectbox("Select Course", c_map.keys(), key="grade_course")
            
            # Fetch Assessments for this course
            assessments = supabase.table("assessments").select("*").eq("course_id", c_map[sel_c]).execute()
            
            # Fetch Students enrolled in this course
            enrollments = supabase.table("student_enrollments").select("profiles(id, email, first_name, last_name)").eq("course_id", c_map[sel_c]).execute()
            
            if assessments.data and enrollments.data:
                a_map = {a["title"]: a["id"] for a in assessments.data}
                sel_a = st.selectbox("Select Assessment", a_map.keys())
                
                s_map = {f"{s['profiles']['first_name']} ({s['profiles']['email']})": s['profiles']['id'] for s in enrollments.data}
                sel_s = st.selectbox("Select Student", s_map.keys())
                
                marks = st.number_input("Marks Obtained", 0.0, float(next(a['max_marks'] for a in assessments.data if a['id'] == a_map[sel_a])))
                
                if st.button("Submit Grade"):
                    supabase.table("grades").upsert({
                        "assessment_id": a_map[sel_a],
                        "student_id": s_map[sel_s],
                        "marks_obtained": marks
                    }).execute()
                    st.success("Grade Recorded!")
            else:
                st.warning("Ensure you have created assessments and students are enrolled.")

# ==================================================
# ====================== STUDENT ===================
# ==================================================
elif role == "student":
    st.title(f"Academic Record: {profile.get('first_name')}")
    
    # 1.7 Stable adds a clean view of grades
    grades = supabase.table("grades").select("marks_obtained, assessments(title, max_marks, type, courses(course_title))").eq("student_id", profile["id"]).execute()
    
    if grades.data:
        # Transform for a nice display
        report = []
        for g in grades.data:
            report.append({
                "Course": g['assessments']['courses']['course_title'],
                "Assessment": g['assessments']['title'],
                "Type": g['assessments']['type'],
                "Score": f"{g['marks_obtained']} / {g['assessments']['max_marks']}"
            })
        st.table(report)
    else:
        st.info("No grades posted yet.")

logout()
