import streamlit as st
import pandas as pd

# 1. Page Setup
st.set_page_config(page_title="Syndicate Manager", layout="wide")
st.title("🎓 Syndicate Project & Grade Manager")

# 2. Sidebar Navigation
menu = ["1. Upload Roster", "2. Student Login/Registration", "3. Faculty Grading", "4. Export Excel"]
choice = st.sidebar.radio("Navigation", menu)

# 3. Data Storage (Persistent for the session)
if 'db' not in st.session_state:
    st.session_state['db'] = pd.DataFrame(columns=[
        'Enrollment', 'Name', 'Email', 'Phone', 'Syndicate Name', 
        'Is Lead', 'Syndicate Grade', 'Individual Grade', 'Course', 'Semester'
    ])

# --- MODULE 1: UPLOAD ROSTER (Admin Only) ---
if choice == "1. Upload Roster":
    st.header("Admin: Upload Class Roster")
    col1, col2 = st.columns(2)
    with col1:
        sem = st.text_input("Semester (e.g., Spring 2026)")
    with col2:
        crs = st.text_input("Course Name")
    
    file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    
    if file and st.button("Process Roster"):
        new_df = pd.read_excel(file)
        # Standardize columns
        new_df['Semester'] = sem
        new_df['Course'] = crs
        new_df['Syndicate Name'] = "Unassigned"
        new_df['Syndicate Grade'] = 0
        new_df['Individual Grade'] = 0
        st.session_state['db'] = pd.concat([st.session_state['db'], new_df], ignore_index=True)
        st.success(f"Successfully loaded {len(new_df)} students!")

# --- MODULE 2: STUDENT REGISTRATION ---
elif choice == "2. Student Login/Registration":
    st.header("Student: Join a Syndicate")
    db = st.session_state['db']
    
    if db.empty:
        st.error("No roster found. Please ask Admin to upload the class list.")
    else:
        # Student searches for their name to "Login"
        student_id = st.selectbox("Select your Enrollment Number", db['Enrollment'].unique())
        
        with st.form("student_form"):
            email = st.text_input("Verify Email Address")
            phone = st.text_input("Cellular Number (Optional)")
            synd_name = st.text_input("Syndicate (Group) Name")
            is_lead = st.checkbox("I am the Syndicate Lead")
            
            if st.form_submit_button("Submit Details"):
                idx = db.index[db['Enrollment'] == student_id]
                db.at[idx[0], 'Email'] = email
                db.at[idx[0], 'Phone'] = phone
                db.at[idx[0], 'Syndicate Name'] = synd_name
                db.at[idx[0], 'Is Lead'] = "Yes" if is_lead else "No"
                st.success("Details updated successfully!")

# --- MODULE 3: FACULTY GRADING ---
elif choice == "3. Faculty Grading":
    st.header("Faculty: Grading Dashboard")
    db = st.session_state['db']
    
    if db.empty:
        st.warning("Roster is empty.")
    else:
        # Filter by Syndicate
        groups = db['Syndicate Name'].unique()
        selected_grp = st.selectbox("Select Syndicate to Grade", groups)
        
        if selected_grp != "Unassigned":
            # Group Grading (Apply to all)
            st.subheader(f"Group Grading: {selected_grp}")
            g_grade = st.number_input("Set Group Grade (applies to everyone)", 0, 100, key="g_input")
            if st.button("Apply Group Grade"):
                db.loc[db['Syndicate Name'] == selected_grp, 'Syndicate Grade'] = g_grade
                st.rerun()

            # Individual Grading
            st.subheader("Individual Adjustments")
            members = db[db['Syndicate Name'] == selected_grp]
            for i, row in members.iterrows():
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"**{row['Name']}** ({row['Enrollment']})")
                new_i_grade = col_b.number_input("Indiv. Grade", 0, 100, value=int(row['Individual Grade']), key=f"ind_{row['Enrollment']}")
                db.at[i, 'Individual Grade'] = new_i_grade

# --- MODULE 4: EXPORT ---
elif choice == "4. Export Excel":
    st.header("Download Final Grades")
    if not st.session_state['db'].empty:
        st.dataframe(st.session_state['db'])
        # Convert to Excel-ready CSV
        csv = st.session_state['db'].to_csv(index=False).encode('utf-8')
        st.download_button("Download as CSV/Excel", data=csv, file_name="syndicate_grades.csv")