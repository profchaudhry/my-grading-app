import streamlit as st
from supabase import create_client
import os

# ==============================
# CONFIG
# ==============================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="SylemaX",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# GLOBAL STYLES
# ==============================

st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

section[data-testid="stSidebar"] {
    background-color: #0f172a;
}
section[data-testid="stSidebar"] * {
    color: white !important;
}

.main-title {
    font-size: 52px;
    font-weight: 800;
    text-align: center;
}
.sub-title {
    font-size: 18px;
    text-align: center;
    color: #64748b;
    margin-bottom: 40px;
}

.card {
    background: white;
    padding: 25px;
    border-radius: 14px;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}

.metric-card {
    background: linear-gradient(135deg,#2563eb,#1e3a8a);
    padding: 20px;
    border-radius: 12px;
    color: white;
    text-align: center;
}
.metric-number {
    font-size: 28px;
    font-weight: 700;
}
.metric-label {
    font-size: 14px;
}
.red-btn button {
    background-color:#dc2626 !important;
    color:white !important;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# SESSION INIT
# ==============================

if "user" not in st.session_state:
    st.session_state.user = None

if "role" not in st.session_state:
    st.session_state.role = None

# ==============================
# LOGIN PAGE
# ==============================

def login_page():

    st.markdown('<div class="main-title">SylemaX</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Let\'s make academic management a breeze</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:

        tab1, tab2 = st.tabs(["Login", "Faculty Registration"])

        # -------- LOGIN TAB --------
        with tab1:
            login_email = st.text_input("Email / Enrollment", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login", key="login_btn"):
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": login_email,
                        "password": login_password
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

        # -------- FACULTY REGISTRATION TAB --------
        with tab2:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            reg_email = st.text_input("Faculty Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("Register Faculty", key="register_btn"):
                try:
                    response = supabase.auth.sign_up({
                        "email": reg_email,
                        "password": reg_password
                    })

                    supabase.table("profiles").insert({
                        "id": response.user.id,
                        "email": reg_email,
                        "role": "faculty",
                        "approved": False
                    }).execute()

                    st.success("Registration submitted for approval.")

                except Exception:
                    st.error("Registration failed.")

# ==============================
# DASHBOARD HEADER
# ==============================

def dashboard_header():

    user = st.session_state.user
    role = st.session_state.role

    profile = supabase.table("profiles")\
        .select("*")\
        .eq("id", user.id)\
        .single()\
        .execute()

    data = profile.data

    st.markdown("## Dashboard")
    st.markdown("### You are logged in as:")

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(f"**Role:** {role.capitalize()}")

    if role == "student":
        st.markdown(f"**Name:** {data.get('first_name','')} {data.get('last_name','')}")
        st.markdown(f"**Enrollment Number:** {data.get('enrollment','')}")
    else:
        st.markdown(f"**Name:** {data.get('first_name','')} {data.get('last_name','')}")
        st.markdown(f"**Email Address:** {data.get('email')}")

    st.markdown('</div>', unsafe_allow_html=True)

# ==============================
# ADMIN CONSOLE
# ==============================

def admin_console():

    st.sidebar.title("Admin Panel")

    menu = st.sidebar.radio(
        "",
        ["Dashboard", "Courses", "Assignments", "Faculty Approvals"],
        key="admin_menu"
    )

    if menu == "Dashboard":

        dashboard_header()

        courses = supabase.table("courses").select("*").execute().data
        faculty = supabase.table("profiles").select("*").eq("role","faculty").execute().data

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-number">{len(courses)}</div>
                <div class="metric-label">Total Courses</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-number">{len(faculty)}</div>
                <div class="metric-label">Faculty Members</div>
            </div>
            """, unsafe_allow_html=True)

    if menu == "Courses":

        st.header("Course Management")

        code = st.text_input("Course Code", key="course_code")
        title = st.text_input("Course Title", key="course_title")
        semester = st.text_input("Semester", key="course_sem")

        if st.button("Create Course", key="create_course_btn"):
            supabase.table("courses").insert({
                "code": code,
                "title": title,
                "semester": semester
            }).execute()
            st.success("Course Created")

        courses = supabase.table("courses").select("*").execute()
        st.dataframe(courses.data)

    if menu == "Assignments":

        st.header("Assign Courses")

        courses = supabase.table("courses").select("*").execute().data
        faculty = supabase.table("profiles")\
            .select("*")\
            .eq("role","faculty")\
            .eq("approved",True)\
            .execute().data

        if courses and faculty:

            course_dict = {c["title"]: c["id"] for c in courses}
            faculty_dict = {f["email"]: f["id"] for f in faculty}

            selected_course = st.selectbox("Select Course", list(course_dict.keys()), key="assign_course")
            selected_faculty = st.selectbox("Select Faculty", list(faculty_dict.keys()), key="assign_faculty")

            if st.button("Assign", key="assign_btn"):
                supabase.table("course_assignments").insert({
                    "course_id": course_dict[selected_course],
                    "faculty_id": faculty_dict[selected_faculty]
                }).execute()
                st.success("Assigned Successfully")
        else:
            st.warning("No courses or approved faculty available.")

    if menu == "Faculty Approvals":

        st.header("Faculty Approvals")

        pending = supabase.table("profiles")\
            .select("*")\
            .eq("role","faculty")\
            .eq("approved",False)\
            .execute()

        if pending.data:
            for f in pending.data:
                col1, col2 = st.columns([4,1])
                col1.write(f["email"])
                if col2.button("Approve", key=f"approve_{f['id']}"):
                    supabase.table("profiles")\
                        .update({"approved":True})\
                        .eq("id",f["id"])\
                        .execute()
                    st.success("Approved")
                    st.rerun()
        else:
            st.success("No pending approvals.")

# ==============================
# ROUTER
# ==============================

if st.session_state.user is None:
    login_page()
else:
    if st.sidebar.button("Logout", key="logout_btn"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()

    if st.session_state.role == "admin":
        admin_console()
