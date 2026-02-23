import streamlit as st
from supabase import create_client
import os

# -----------------------------
# CONFIG
# -----------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="SylemaX",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# SESSION INIT
# -----------------------------

if "user" not in st.session_state:
    st.session_state.user = None

if "role" not in st.session_state:
    st.session_state.role = None

# -----------------------------
# LOGIN PAGE
# -----------------------------

def login_page():

    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display:none;}
            .main-title {font-size:48px; font-weight:700; text-align:center;}
            .sub-title {font-size:20px; text-align:center; margin-bottom:40px; color:gray;}
            .red-button button {background-color:#e63946; color:white; font-weight:600;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">SylemaX</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Let\'s make academic management a breeze</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Faculty Registration"])

    with tab1:
        email = st.text_input("Email / Enrollment Number")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            try:
                response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                user = response.user

                profile = supabase.table("profiles")\
                    .select("*")\
                    .eq("id", user.id)\
                    .single()\
                    .execute()

                st.session_state.user = user
                st.session_state.role = profile.data["role"]
                st.rerun()

            except Exception:
                st.error("Invalid credentials")

    with tab2:
        st.markdown('<div class="red-button">', unsafe_allow_html=True)
        email = st.text_input("Faculty Email")
        password = st.text_input("Password", type="password")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Register Faculty"):
            try:
                response = supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })

                supabase.table("profiles").insert({
                    "id": response.user.id,
                    "email": email,
                    "role": "faculty",
                    "approved": False
                }).execute()

                st.success("Registration submitted. Await admin approval.")
            except Exception:
                st.error("Registration failed.")

# -----------------------------
# DASHBOARD HEADER
# -----------------------------

def dashboard_header():

    st.title("Dashboard")
    st.markdown("### You are logged in as:")

    role = st.session_state.role
    user = st.session_state.user

    profile = supabase.table("profiles")\
        .select("*")\
        .eq("id", user.id)\
        .single()\
        .execute()

    data = profile.data

    st.markdown(f"**Role:** {role.capitalize()}")

    if role == "student":
        st.markdown(f"**Name:** {data.get('first_name','')} {data.get('last_name','')}")
        st.markdown(f"**Enrollment Number:** {data.get('enrollment','')}")

    else:
        st.markdown(f"**Name:** {data.get('first_name','')} {data.get('last_name','')}")
        st.markdown(f"**Email Address:** {data.get('email')}")

    st.divider()

# -----------------------------
# ADMIN CONSOLE
# -----------------------------

def admin_console():

    st.sidebar.title("Admin Panel")

    menu = st.sidebar.radio(
        "Navigate",
        [
            "Dashboard",
            "Manage Courses",
            "Assign Courses",
            "Faculty Approvals"
        ]
    )

    if menu == "Dashboard":
        dashboard_header()

    if menu == "Manage Courses":
        st.header("Manage Courses")

        code = st.text_input("Course Code")
        title = st.text_input("Course Title")
        semester = st.text_input("Semester")

        if st.button("Create Course"):
            supabase.table("courses").insert({
                "code": code,
                "title": title,
                "semester": semester
            }).execute()

            st.success("Course Created")

        courses = supabase.table("courses").select("*").execute()
        st.dataframe(courses.data)

    if menu == "Assign Courses":
        st.header("Assign Courses")

        courses = supabase.table("courses").select("*").execute().data
        faculty = supabase.table("profiles")\
            .select("*")\
            .eq("role","faculty")\
            .eq("approved",True)\
            .execute().data

        course_dict = {c["title"]: c["id"] for c in courses}
        faculty_dict = {f["email"]: f["id"] for f in faculty}

        selected_course = st.selectbox("Select Course", list(course_dict.keys()))
        selected_faculty = st.selectbox("Select Faculty", list(faculty_dict.keys()))

        if st.button("Assign"):
            supabase.table("course_assignments").insert({
                "course_id": course_dict[selected_course],
                "faculty_id": faculty_dict[selected_faculty]
            }).execute()

            st.success("Course Assigned")

    if menu == "Faculty Approvals":
        st.header("Faculty Approvals")

        pending = supabase.table("profiles")\
            .select("*")\
            .eq("role","faculty")\
            .eq("approved",False)\
            .execute()

        for f in pending.data:
            col1, col2 = st.columns([3,1])
            col1.write(f["email"])
            if col2.button("Approve", key=f["id"]):
                supabase.table("profiles")\
                    .update({"approved":True})\
                    .eq("id",f["id"])\
                    .execute()
                st.success("Approved")
                st.rerun()

# -----------------------------
# FACULTY CONSOLE
# -----------------------------

def faculty_console():

    st.sidebar.title("Faculty Panel")

    menu = st.sidebar.radio(
        "Navigate",
        [
            "Dashboard",
            "My Courses",
            "My Profile"
        ]
    )

    dashboard_header()

    if menu == "My Courses":
        st.header("Assigned Courses")

        user_id = st.session_state.user.id

        assignments = supabase.table("course_assignments")\
            .select("courses(title,code,semester)")\
            .eq("faculty_id",user_id)\
            .execute()

        st.write(assignments.data)

    if menu == "My Profile":
        st.header("Faculty Profile")

        user_id = st.session_state.user.id

        profile = supabase.table("profiles")\
            .select("*")\
            .eq("id",user_id)\
            .single()\
            .execute()

        data = profile.data

        first = st.text_input("First Name", value=data.get("first_name",""))
        last = st.text_input("Last Name", value=data.get("last_name",""))
        designation = st.text_input("Designation", value=data.get("designation",""))
        department = st.text_input("Department", value=data.get("department",""))
        mobile = st.text_input("Mobile", value=data.get("mobile",""))
        office = st.text_input("Office Address", value=data.get("office",""))
        campus = st.text_input("Campus", value=data.get("campus",""))
        city = st.text_input("City", value=data.get("city",""))
        institution = st.text_input("Institution", value=data.get("institution",""))

        if st.button("Update Profile"):
            supabase.table("profiles").update({
                "first_name": first,
                "last_name": last,
                "designation": designation,
                "department": department,
                "mobile": mobile,
                "office": office,
                "campus": campus,
                "city": city,
                "institution": institution
            }).eq("id",user_id).execute()

            st.success("Profile Updated")

# -----------------------------
# STUDENT CONSOLE
# -----------------------------

def student_console():

    st.sidebar.title("Student Panel")

    dashboard_header()

# -----------------------------
# ROUTER
# -----------------------------

if st.session_state.user is None:
    login_page()
else:
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()

    if st.session_state.role == "admin":
        admin_console()

    elif st.session_state.role == "faculty":
        faculty_console()

    elif st.session_state.role == "student":
        student_console()
