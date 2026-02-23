import streamlit as st
from utils.db import supabase

st.set_page_config(page_title="SylemaX", layout="wide")

# =========================
# SESSION STATE INIT
# =========================
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.profile = None


# =========================
# LOGIN PAGE (NO SIDEBAR)
# =========================
def login():

    st.markdown("<h1 style='text-align:center;'>SylemaX</h1>", unsafe_allow_html=True)
    st.markdown(
        "<h4 style='text-align:center;'>Let's make academic management a breeze</h4>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    role = st.selectbox("Select Role", ["Student", "Faculty", "Admin"])

    username_label = "Enrollment Number" if role == "Student" else "Email"
    username = st.text_input(username_label)
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    # -------- STUDENT LOGIN --------
    if role == "Student":
        if col1.button("Login"):
            try:
                response = supabase.auth.sign_in_with_password({
                    "email": f"{username}@student.local",
                    "password": password
                })
                if response.user:
                    profile = supabase.table("profiles") \
                        .select("*") \
                        .eq("id", response.user.id) \
                        .single() \
                        .execute().data

                    st.session_state.user = response.user
                    st.session_state.profile = profile
                    st.rerun()
            except:
                st.error("Invalid login credentials.")

    # -------- FACULTY LOGIN --------
    if role == "Faculty":
        if col1.button("Login"):
            try:
                response = supabase.auth.sign_in_with_password({
                    "email": username,
                    "password": password
                })
                if response.user:
                    profile = supabase.table("profiles") \
                        .select("*") \
                        .eq("id", response.user.id) \
                        .single() \
                        .execute().data

                    if profile["role"] == "pending_faculty":
                        st.warning("Awaiting admin approval.")
                        return

                    st.session_state.user = response.user
                    st.session_state.profile = profile
                    st.rerun()
            except:
                st.error("Invalid login credentials.")

        # Red Faculty Registration Button
        st.markdown(
            """
            <style>
            div.stButton > button:first-child {
                background-color: #d11a2a;
                color: white;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        if col2.button("Register as Faculty"):
            try:
                response = supabase.auth.sign_up({
                    "email": username,
                    "password": password
                })
                if response.user:
                    supabase.table("profiles").insert({
                        "id": response.user.id,
                        "email": username,
                        "role": "pending_faculty",
                        "must_change_password": False
                    }).execute()
                    st.success("Registration successful. Await admin approval.")
            except:
                st.error("Registration failed.")

    # -------- ADMIN LOGIN --------
    if role == "Admin":
        if col1.button("Login"):
            try:
                response = supabase.auth.sign_in_with_password({
                    "email": username,
                    "password": password
                })
                if response.user:
                    profile = supabase.table("profiles") \
                        .select("*") \
                        .eq("id", response.user.id) \
                        .single() \
                        .execute().data

                    if profile["role"] not in ["admin", "faculty_pro"]:
                        st.error("Unauthorized access.")
                        return

                    st.session_state.user = response.user
                    st.session_state.profile = profile
                    st.rerun()
            except:
                st.error("Invalid login credentials.")


# =========================
# LOGOUT
# =========================
def logout():
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.profile = None
        st.rerun()


# =========================
# MAIN ROUTING
# =========================
if not st.session_state.user:
    login()
    st.stop()

profile = st.session_state.profile
role = profile["role"]

# =========================
# SIDEBAR AFTER LOGIN
# =========================
st.sidebar.title("Navigation")
st.sidebar.write(f"Role: {role}")

# =========================
# DASHBOARD HEADER (ALL ROLES)
# =========================
st.title("Dashboard")
st.markdown("### You are logged in as:")

if role in ["faculty", "faculty_pro"]:
    st.write("**Faculty**")
    st.write(f"Name: {profile.get('first_name', '')} {profile.get('last_name', '')}")
    st.write(f"Email Address: {profile.get('email')}")

elif role == "admin":
    st.write("**Admin**")
    st.write(f"Name: {profile.get('first_name', '')} {profile.get('last_name', '')}")
    st.write(f"Email Address: {profile.get('email')}")

elif role == "student":
    st.write("**Student**")
    st.write(f"Name: {profile.get('first_name', '')} {profile.get('last_name', '')}")
    st.write(f"Enrollment Number: {profile.get('email').split('@')[0]}")

st.markdown("---")

# =========================
# ROLE CONTENT
# =========================
if role == "admin":
    st.subheader("Admin Console")

elif role in ["faculty", "faculty_pro"]:
    st.subheader("Faculty Console")

elif role == "student":
    st.subheader("Student Console")

logout()
