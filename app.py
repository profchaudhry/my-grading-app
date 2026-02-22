import streamlit as st
from utils.auth import login, logout, enforce_password_change
from utils.db import supabase

st.set_page_config(page_title="UCS System", layout="wide")


# ==========================================
# SESSION CHECK
# ==========================================
if "user" not in st.session_state:
    login()
    st.stop()


profile = st.session_state.profile
role = profile["role"]

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("UCS Navigation")
st.sidebar.write(f"Logged in as: {role}")

enforce_password_change()


# ==========================================
# ================= ADMIN ==================
# ==========================================
if role == "admin":

    page = st.sidebar.radio(
        "Admin Menu",
        [
            "Dashboard",
            "Approve Faculty",
            "View All Profiles"
        ]
    )

    if page == "Dashboard":
        st.title("Admin Dashboard")
        st.write("Welcome Administrator.")

    # --------------------------------------
    # APPROVE FACULTY
    # --------------------------------------
    if page == "Approve Faculty":

        st.title("Approve Faculty")

        pending = supabase.table("profiles") \
            .select("*") \
            .eq("role", "pending_faculty") \
            .execute()

        if not pending.data:
            st.success("No pending faculty approvals.")
        else:
            for faculty in pending.data:
                col1, col2 = st.columns([4, 1])

                col1.write(faculty["email"])

                if col2.button(
                    "Approve",
                    key=faculty["id"]
                ):
                    supabase.table("profiles").update({
                        "role": "faculty"
                    }).eq("id", faculty["id"]).execute()

                    st.success("Faculty Approved")
                    st.rerun()

    # --------------------------------------
    # VIEW ALL PROFILES
    # --------------------------------------
    if page == "View All Profiles":

        st.title("All Users")

        users = supabase.table("profiles") \
            .select("*") \
            .execute()

        st.dataframe(users.data)


# ==========================================
# =============== FACULTY ==================
# ==========================================
elif role in ["faculty", "faculty_pro"]:

    page = st.sidebar.radio(
        "Faculty Menu",
        [
            "Dashboard",
            "My Profile"
        ]
    )

    if page == "Dashboard":
        st.title("Faculty Dashboard")
        st.write("Welcome Faculty Member.")

    # --------------------------------------
    # FACULTY PROFILE
    # --------------------------------------
    if page == "My Profile":

        st.title("My Profile")

        with st.form("faculty_profile_form"):

            first_name = st.text_input("First Name", profile.get("first_name", ""))
            last_name = st.text_input("Last Name", profile.get("last_name", ""))
            designation = st.text_input("Designation", profile.get("designation", ""))
            department = st.text_input("Department", profile.get("department", ""))
            mobile = st.text_input("Mobile", profile.get("mobile", ""))
            office = st.text_input("Office Address", profile.get("office_address", ""))
            campus = st.text_input("Campus", profile.get("campus", ""))
            city = st.text_input("City", profile.get("city", ""))
            institution = st.text_input("Affiliated Institution", profile.get("institution", ""))

            submitted = st.form_submit_button("Update Profile")

            if submitted:

                supabase.table("profiles").update({
                    "first_name": first_name,
                    "last_name": last_name,
                    "designation": designation,
                    "department": department,
                    "mobile": mobile,
                    "office_address": office,
                    "campus": campus,
                    "city": city,
                    "institution": institution
                }).eq("id", profile["id"]).execute()

                st.success("Profile Updated")
                st.rerun()


# ==========================================
# =============== STUDENT ==================
# ==========================================
elif role == "student":

    page = st.sidebar.radio(
        "Student Menu",
        [
            "Dashboard"
        ]
    )

    if page == "Dashboard":
        st.title("Student Dashboard")
        st.write("Welcome Student.")


# ==========================================
# UNKNOWN ROLE
# ==========================================
else:
    st.error("Role not recognized.")


# ==========================================
# LOGOUT
# ==========================================
logout()
