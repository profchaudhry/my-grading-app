import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Sylemas", layout="wide")

# -----------------------------
# SUPABASE CONNECTION
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# AUTH FUNCTIONS
# -----------------------------
def sign_up(email, password):
    response = supabase.auth.sign_up({"email": email, "password": password})
    return response

def sign_in(email, password):
    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
    return response

def create_profile(user):
    supabase.table("profiles").upsert({
        "id": user.id,
        "email": user.email,
        "role": "student"
    }).execute()

def get_user_profile(user_id):
    response = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if response.data:
        return response.data[0]
    return None

# -----------------------------
# LOGIN UI
# -----------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:

    st.title("🔐 Sylemas Login")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            try:
                user = sign_in(email, password)
                st.session_state.user = user.user
                st.rerun()
            except:
                st.error("Invalid login credentials")

    with tab2:
        new_email = st.text_input("New Email")
        new_password = st.text_input("New Password", type="password")
        if st.button("Register"):
            try:
                user = sign_up(new_email, new_password)
                create_profile(user.user)
                st.success("Registration successful. Please login.")
            except:
                st.error("Registration failed.")

    st.stop()

# -----------------------------
# LOAD USER ROLE
# -----------------------------
profile = get_user_profile(st.session_state.user.id)
role = profile["role"]

st.sidebar.success(f"Logged in as: {profile['email']}")
st.sidebar.info(f"Role: {role}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# -----------------------------
# ROLE-BASED MENU
# -----------------------------
menu = []

if role == "admin":
    menu.append("Upload Roster")

if role == "faculty":
    menu.append("Faculty Grading")
    menu.append("Export Data")

if role == "student":
    menu.append("Student Registration")

choice = st.sidebar.radio("Navigation", menu)

# -----------------------------
# STUDENT MODULE
# -----------------------------
if choice == "Student Registration":
    st.header("Student Dashboard")
    st.write("Student functionality here")

# -----------------------------
# FACULTY MODULE
# -----------------------------
elif choice == "Faculty Grading":
    st.header("Faculty Dashboard")
    st.write("Faculty grading functionality here")

# -----------------------------
# ADMIN MODULE
# -----------------------------
elif choice == "Upload Roster":
    st.header("Admin Dashboard")
    st.write("Roster upload functionality here")

# -----------------------------
# EXPORT MODULE
# -----------------------------
elif choice == "Export Data":
    st.header("Export Dashboard")
    st.write("Export functionality here")
