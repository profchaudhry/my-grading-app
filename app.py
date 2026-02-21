import streamlit as st
import pandas as pd
from supabase import create_client, Client

# -----------------------------
# 1. PAGE CONFIG & CLIENT INIT
# -----------------------------
st.set_page_config(page_title="Sylemas", layout="wide", page_icon="🎓")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# -----------------------------
# 2. DATABASE UTILITIES
# -----------------------------
def load_students():
    try:
        response = supabase.table("students").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading students: {e}")
        return pd.DataFrame()

def get_user_profile(user_id):
    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        return res.data
    except:
        return None

def update_student_record(enrollment, data):
    return supabase.table("students").update(data).eq("enrollment", enrollment).execute()

# -----------------------------
# 3. AUTHENTICATION UI
# -----------------------------
def auth_ui():
    st.title("🎓 Sylemas — Syndicate LMS")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error("Invalid credentials or user not found.")

    with tab2:
        with st.form("reg_form"):
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            if st.form_submit_button("Create Account", use_container_width=True):
                try:
                    res = supabase.auth.sign_up({"email": new_email, "password": new_password})
                    if res.user:
                        # Create profile entry
                        supabase.table("profiles").upsert({"id": res.user.id, "email": new_email, "role": "student"}).execute()
                        st.success("Account created! You can now login.")
                except Exception as e:
                    st.error(f"Registration failed: {e}")

# -----------------------------
# 4. MAIN APP LOGIC
# -----------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    auth_ui()
    st.stop()

# Load User Profile
profile = get_user_profile(st.session_state.user.id)
if not profile:
    st.error("Profile not found. Please contact Admin.")
    st.stop()

role = profile["role"]

# Sidebar Navigation
st.sidebar.title("Sylemas")
st.sidebar.markdown(f"**User:** `{profile['email']}`\n**Role:** `{role.capitalize()}`")

menu = ["Home"]
if role == "admin": menu += ["Upload Roster"]
if role in ["faculty", "admin"]: menu += ["Faculty Grading", "Export Data"]
if role == "student": menu += ["Student Registration"]

choice = st.sidebar.radio("Navigation", menu)

if st.sidebar.button("Logout"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- MODULE: Home ---
if choice == "Home":
    st.header(f"Welcome to Sylemas, {profile['email']}!")
    st.write("Use the sidebar to navigate through your assigned tasks.")

# --- MODULE: Upload Roster (Admin) ---
elif choice == "Upload Roster":
    st.header("Admin: Batch Upload Roster")
    semester = st.text_input("Semester (e.g., Spring 2026)")
    course = st.text_input("Course Name")
    file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    
    if file and st.button("Process Roster"):
        df = pd.read_excel(file)
        if all(col in df.columns for col in ["Enrollment", "Name"]):
            with st.spinner("Uploading..."):
                for _, row in df.iterrows():
                    supabase.table("students").upsert({
                        "enrollment": str(row["Enrollment"]),
                        "name": row["Name"],
                        "course": course,
                        "semester": semester
                    }).execute()
            st.success("Roster updated successfully!")
        else:
            st.error("Missing 'Enrollment' or 'Name' columns.")

# --- MODULE: Student Registration ---
elif choice == "Student Registration":
    st.header("Join Your Syndicate")
    db = load_students()
    if db.empty:
        st.warning("No roster found.")
    else:
        # Check if student already registered to find their record
        student_id = st.selectbox("Confirm your Enrollment Number", db["enrollment"].unique())
        rec = db[db["enrollment"] == student_id].iloc[0]
        
        with st.form("reg_student"):
            s_phone = st.text_input("Phone Number", value=rec.get("phone", "") or "")
            s_syndicate = st.text_input("Syndicate Name", value=rec.get("syndicate_name", "Unassigned"))
            s_lead = st.checkbox("Syndicate Lead?", value=bool(rec.get("is_lead", False)))
            
            if st.form_submit_button("Update My Info"):
                update_student_record(student_id, {
                    "email": profile["email"],
                    "phone": s_phone,
                    "syndicate_name": s_syndicate,
                    "is_lead": s_lead
                })
                st.toast("Profile Updated!", icon="✅")

# --- MODULE: Faculty Grading ---
elif choice == "Faculty Grading":
    st.header("Faculty Grading Panel")
    db = load_students()
    
    if not db.empty:
        # Filter groups
        groups = [g for g in db["syndicate_name"].unique() if g and g != "Unassigned"]
        selected_group = st.selectbox("Select Syndicate to Grade", groups)
        
        if selected_group:
            members = db[db["syndicate_name"] == selected_group]
            
            with st.form("batch_grading_form"):
                st.subheader(f"Grading: {selected_group}")
                
                # Bulk Group Grade
                g_grade = st.number_input("Standard Group Grade", 0, 100, step=5)
                apply_all = st.checkbox("Override all individual grades with group grade?")
                
                st.divider()
                
                individual_updates = {}
                for _, member in members.iterrows():
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"**{member['name']}** ({member['enrollment']})")
                    current_val = int(member.get("individual_grade", 0)) if member.get("individual_grade") else 0
                    individual_updates[member["enrollment"]] = col2.number_input(
                        "Grade", 0, 100, value=g_grade if apply_all else current_val, key=member["enrollment"]
                    )
                
                if st.form_submit_button("Save All Grades"):
                    for eid, grade in individual_updates.items():
                        update_student_record(eid, {"individual_grade": grade, "syndicate_grade": g_grade})
                    st.toast("Grades Saved Successfully!", icon="🚀")
                    st.rerun()

# --- MODULE: Export Data ---
elif choice == "Export Data":
    st.header("Download Data")
    db = load_students()
    if not db.empty:
        st.dataframe(db, use_container_width=True)
        csv = db.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="sylemas_data.csv", mime="text/csv")
