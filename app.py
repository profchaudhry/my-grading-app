import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Sylemas UCS1.2", layout="wide")
st.title("🎓 Sylemas — UCS1.2")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------
# SESSION INIT
# ---------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------------------------
# DATABASE HELPERS
# ---------------------------------
def get_profile(user_id):
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def update_profile(user_id, data):
    supabase.table("profiles").update(data).eq("id", user_id).execute()

def load_students():
    res = supabase.table("students").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def update_student(enrollment, data):
    supabase.table("students").update(data).eq("enrollment", enrollment).execute()

# ---------------------------------
# LOGIN SCREEN
# ---------------------------------
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

            actual_role = profile["role"]

            expected_role = role_selected.lower().replace(" ", "_")

            if actual_role != expected_role:
                st.error("Incorrect role selected.")
                st.stop()

            st.session_state.user = response.user
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.stop()

# ---------------------------------
# AFTER LOGIN
# ---------------------------------
profile = get_profile(st.session_state.user.id)
role = profile["role"]

st.sidebar.success(f"Logged in as: {profile['email']}")
st.sidebar.info(f"Role: {role}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ---------------------------------
# FORCE PASSWORD CHANGE
# ---------------------------------
if profile["must_change_password"]:
    st.warning("You must change your password.")
    new_pass = st.text_input("New Password", type="password")
    if st.button("Update Password"):
        supabase.auth.update_user({"password": new_pass})
        update_profile(st.session_state.user.id, {"must_change_password": False})
        st.success("Password updated.")
        st.rerun()
    st.stop()

# ---------------------------------
# MENU BASED ON ROLE
# ---------------------------------
menu = []

if role in ["admin", "faculty_pro"]:
    menu.append("Upload Roster")
    menu.append("Approve Faculty")

if role in ["faculty", "faculty_pro"]:
    menu.append("Faculty Grading")

if role == "student":
    menu.append("Student Dashboard")

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

            # Create auth user
            user = supabase.auth.admin.create_user({
                "email": f"{enrollment}@student.local",
                "password": "ChangerYourPassword1@#4"
            })

            # Insert profile
            supabase.table("profiles").insert({
                "id": user.user.id,
                "email": f"{enrollment}@student.local",
                "role": "student",
                "enrollment": enrollment,
                "must_change_password": True
            }).execute()

            # Insert student record
            supabase.table("students").upsert({
                "enrollment": enrollment,
                "name": name,
                "course": course,
                "semester": semester
            }).execute()

        st.success("Roster uploaded and student accounts created.")

# =====================================
# STUDENT DASHBOARD
# =====================================
elif choice == "Student Dashboard":

    st.header("My Profile")

    enrollment = profile["enrollment"]

    db = load_students()
    student = db[db["enrollment"] == enrollment].iloc[0]

    email = st.text_input("Email", value=student.get("email", ""))
    phone = st.text_input("Phone", value=student.get("phone", ""))

    if st.button("Update"):
        update_student(enrollment, {"email": email, "phone": phone})
        st.success("Updated successfully.")

# =====================================
# FACULTY GRADING
# =====================================
elif choice == "Faculty Grading":

    st.header("Grading Dashboard")

    db = load_students()

    if db.empty:
        st.warning("No students found.")
    else:
        groups = db["syndicate_name"].dropna().unique()
        selected = st.selectbox("Select Syndicate", groups)

        grade = st.number_input("Group Grade", 0, 100)

        if st.button("Apply Grade"):
            supabase.table("students")\
                .update({"syndicate_grade": grade})\
                .eq("syndicate_name", selected)\
                .execute()

            st.success("Grade applied.")

# =====================================
# APPROVE FACULTY
# =====================================
elif choice == "Approve Faculty":

    st.header("Approve Faculty")

    pending = supabase.table("profiles")\
        .select("*")\
        .eq("role", "pending_faculty")\
        .execute()

    for p in pending.data:
        st.write(p["email"])
        if st.button(f"Approve {p['email']}"):
            update_profile(p["id"], {"role": "faculty"})
            st.success("Faculty approved.")
