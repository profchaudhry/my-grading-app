import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Sylemas UCS1.3", layout="wide")
st.title("🎓 Sylemas — UCS1.3")

# -----------------------------
# SUPABASE CONNECTION
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# SESSION INIT
# -----------------------------
if "user" not in st.session_state:
    st.session_state.user = None

# -----------------------------
# HELPERS
# -----------------------------
def get_profile(user_id):
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def update_profile(user_id, data):
    supabase.table("profiles").update(data).eq("id", user_id).execute()

def load_students():
    res = supabase.table("students").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# -----------------------------
# LOGIN
# -----------------------------
if not st.session_state.user:

    st.header("🔐 Login")

    role_selected = st.selectbox(
        "Login As",
        ["Student", "Faculty", "Admin", "Faculty Pro"]
    )

    if role_selected == "Student":
        username = st.text_input("Enrollment Number")
    else:
        username = st.text_input("Email")

    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role_selected == "Student":
            login_email = f"{username}@student.local"
        else:
            login_email = username

        response = supabase.auth.sign_in_with_password({
            "email": login_email,
            "password": password
        })

        if response.user:
            profile = get_profile(response.user.id)

            if not profile:
                st.error("Profile not found.")
                st.stop()

            expected_role = role_selected.lower().replace(" ", "_")

            if profile["role"] != expected_role:
                st.error("Incorrect role selected.")
                st.stop()

            st.session_state.user = response.user
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.stop()

# -----------------------------
# AFTER LOGIN
# -----------------------------
profile = get_profile(st.session_state.user.id)
role = profile["role"]

st.sidebar.success(f"Logged in as: {profile['email']}")
st.sidebar.info(f"Role: {role}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# -----------------------------
# FORCE PASSWORD CHANGE
# -----------------------------
if profile.get("must_change_password", False):
    st.warning("You must change your password.")
    new_pass = st.text_input("New Password", type="password")
    if st.button("Update Password"):
        supabase.auth.update_user({"password": new_pass})
        update_profile(st.session_state.user.id, {"must_change_password": False})
        st.success("Password updated.")
        st.rerun()
    st.stop()

# -----------------------------
# ROLE MENU
# -----------------------------
menu = []

if role in ["admin", "faculty_pro"]:
    menu += ["Upload Roster", "Manage Courses", "Assign Courses", "Approve Faculty", "View Faculty Profiles"]

if role in ["faculty", "faculty_pro"]:
    menu += ["Faculty Dashboard", "My Faculty Profile"]

if role == "student":
    menu += ["Student Dashboard"]

choice = st.sidebar.radio("Navigation", menu)

# =====================================
# ADMIN — UPLOAD ROSTER
# =====================================
if choice == "Upload Roster":

    st.header("Upload Class Roster")

    semester = st.text_input("Semester")
    course = st.text_input("Course")
    file = st.file_uploader("Upload Excel", type=["xlsx"])

    if file and st.button("Process"):

        df = pd.read_excel(file)

        for _, row in df.iterrows():

            enrollment = str(row["Enrollment"])
            name = row["Name"]

            user = supabase.auth.admin.create_user({
                "email": f"{enrollment}@student.local",
                "password": "ChangerYourPassword1@#4"
            })

            supabase.table("profiles").insert({
                "id": user.user.id,
                "email": f"{enrollment}@student.local",
                "role": "student",
                "enrollment": enrollment,
                "must_change_password": True
            }).execute()

            supabase.table("students").upsert({
                "enrollment": enrollment,
                "name": name,
                "course": course,
                "semester": semester
            }).execute()

        st.success("Roster uploaded and student accounts created.")

# =====================================
# ADMIN — MANAGE COURSES
# =====================================
elif choice == "Manage Courses":

    st.header("Create Course")

    code = st.text_input("Course Code")
    title = st.text_input("Course Title")
    semester = st.text_input("Semester")

    if st.button("Create Course"):
        supabase.table("courses").insert({
            "course_code": code,
            "course_title": title,
            "semester": semester
        }).execute()
        st.success("Course created.")

# =====================================
# ADMIN — ASSIGN COURSES
# =====================================
elif choice == "Assign Courses":

    st.header("Assign Course to Faculty")

    faculty = supabase.table("profiles")\
        .select("*")\
        .in_("role", ["faculty", "faculty_pro"])\
        .execute()

    courses = supabase.table("courses").select("*").execute()

    if faculty.data and courses.data:

        faculty_map = {f["email"]: f["id"] for f in faculty.data}
        course_map = {c["course_code"]: c["id"] for c in courses.data}

        selected_faculty = st.selectbox("Select Faculty", list(faculty_map.keys()))
        selected_course = st.selectbox("Select Course", list(course_map.keys()))

        if st.button("Assign"):
            supabase.table("faculty_courses").insert({
                "faculty_id": faculty_map[selected_faculty],
                "course_id": course_map[selected_course]
            }).execute()

            st.success("Course assigned successfully.")
    else:
        st.warning("No faculty or courses found.")

# =====================================
# ADMIN — APPROVE FACULTY
# =====================================
elif choice == "Approve Faculty":

    st.header("Approve Faculty")

    pending = supabase.table("profiles")\
        .select("*")\
        .eq("role", "pending_faculty")\
        .execute()

    if pending.data:
        for p in pending.data:
            st.write(p["email"])
            if st.button(f"Approve {p['email']}"):
                update_profile(p["id"], {"role": "faculty"})
                st.success("Faculty approved.")
    else:
        st.info("No pending faculty.")

# =====================================
# ADMIN — VIEW ALL FACULTY PROFILES
# =====================================
elif choice == "View Faculty Profiles":

    st.header("All Faculty Profiles")

    profiles = supabase.table("faculty_profiles").select("*").execute()

    if profiles.data:
        df = pd.DataFrame(profiles.data)
        st.dataframe(df)
    else:
        st.info("No faculty profiles found.")

# =====================================
# FACULTY DASHBOARD
# =====================================
elif choice == "Faculty Dashboard":

    st.header("My Assigned Courses")

    assigned = supabase.table("faculty_courses")\
        .select("courses(*)")\
        .eq("faculty_id", st.session_state.user.id)\
        .execute()

    if assigned.data:
        course_list = [c["courses"]["course_code"] for c in assigned.data]
        st.selectbox("Assigned Courses", course_list)
    else:
        st.warning("No courses assigned.")

# =====================================
# FACULTY PROFILE
# =====================================
elif choice == "My Faculty Profile":

    st.header("Faculty Profile")

    existing = supabase.table("faculty_profiles")\
        .select("*")\
        .eq("id", st.session_state.user.id)\
        .execute()

    data = existing.data[0] if existing.data else {}

    first = st.text_input("First Name", value=data.get("first_name", ""))
    last = st.text_input("Last Name", value=data.get("last_name", ""))
    designation = st.text_input("Designation", value=data.get("designation", ""))
    department = st.text_input("Department", value=data.get("department", ""))
    mobile = st.text_input("Mobile", value=data.get("mobile", ""))
    office = st.text_input("Office Address", value=data.get("office_address", ""))
    campus = st.text_input("Campus", value=data.get("campus", ""))
    city = st.text_input("City", value=data.get("city", ""))
    institution = st.text_input("Institution", value=data.get("institution", ""))
    bio = st.text_area("Biography", value=data.get("biography", ""))

    if st.button("Save Profile"):

        payload = {
            "id": st.session_state.user.id,
            "first_name": first,
            "last_name": last,
            "designation": designation,
            "department": department,
            "mobile": mobile,
            "office_address": office,
            "campus": campus,
            "city": city,
            "institution": institution,
            "biography": bio
        }

        supabase.table("faculty_profiles").upsert(payload).execute()
        st.success("Profile saved.")

# =====================================
# STUDENT DASHBOARD
# =====================================
elif choice == "Student Dashboard":

    st.header("My Profile")

    enrollment = profile["enrollment"]

    students = load_students()
    student = students[students["enrollment"] == enrollment].iloc[0]

    email = st.text_input("Email", value=student.get("email", ""))
    phone = st.text_input("Phone", value=student.get("phone", ""))

    if st.button("Update"):
        supabase.table("students")\
            .update({"email": email, "phone": phone})\
            .eq("enrollment", enrollment)\
            .execute()

        st.success("Updated successfully.")
