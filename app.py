'''import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Faculty Preference System", layout="wide")
st.title("📊 Faculty Preference System")

SPREADSHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"

# -----------------------------
# GOOGLE AUTH
# -----------------------------
@st.cache_resource
def get_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)

client = get_client()

# -----------------------------
# SPREADSHEET
# -----------------------------
@st.cache_resource
def get_spreadsheet():
    return client.open_by_key(SPREADSHEET_ID)

ss = get_spreadsheet()
response_sheet = ss.get_worksheet(0)

# -----------------------------
# LOAD SHEET
# -----------------------------
@st.cache_data(ttl=60)
def load_sheet(index):
    sheet = ss.get_worksheet(index)
    data = sheet.get_all_values()

    df = pd.DataFrame(data[1:], columns=data[0])
    df.columns = df.columns.str.strip()

    return df

# -----------------------------
# LOAD DATA
# -----------------------------
b1_df = load_sheet(1)   # Basket 1
b2_df = load_sheet(2)   # Basket 2
faculty_df = load_sheet(3)  # Faculty List

# -----------------------------
# GET COURSE LIST
# -----------------------------
def get_course_list(df):
    course_col = None

    for col in df.columns:
        if "course" in col.lower():
            course_col = col
            break

    if course_col is None:
        st.error(f"Course column not found. Columns: {df.columns.tolist()}")
        st.stop()

    return df[course_col].dropna().astype(str).tolist()

basket1 = get_course_list(b1_df)
basket2 = get_course_list(b2_df)

# -----------------------------
# FACULTY CLEANUP
# -----------------------------
faculty_df.columns = faculty_df.columns.str.strip()
faculty_df["EmpID"] = faculty_df["EmpID"].astype(str).str.strip()

# -----------------------------
# EMP ID INPUT
# -----------------------------
emp_id = st.text_input("Enter Employee ID").strip()

name = ""
designation = ""

if emp_id:
    match = faculty_df[faculty_df["EmpID"] == emp_id]

    if not match.empty:
        name = match.iloc[0]["Name"]
        designation = match.iloc[0]["Designation"]
    else:
        st.warning("❌ Employee ID not found")

st.text_input("Name", value=name, disabled=True)
st.text_input("Designation", value=designation, disabled=True)

# -----------------------------
# UI
# -----------------------------
col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1
# -----------------------------
with col1:
    st.subheader("📘 Basket 1")

    b1_selected = []
    available_b1 = basket1.copy()

    for i in range(7):
        choice = st.selectbox(
            f"B1 Choice {i+1}",
            ["Select"] + available_b1,
            key=f"b1_{i}"
        )

        if choice != "Select":
            b1_selected.append(choice)
            if choice in available_b1:
                available_b1.remove(choice)

# -----------------------------
# BASKET 2
# -----------------------------
with col2:
    st.subheader("📗 Basket 2")

    b2_selected = []
    available_b2 = basket2.copy()

    for i in range(7):
        choice = st.selectbox(
            f"B2 Choice {i+1}",
            ["Select"] + available_b2,
            key=f"b2_{i}"
        )

        if choice != "Select":
            b2_selected.append(choice)
            if choice in available_b2:
                available_b2.remove(choice)

# -----------------------------
# SUBMIT (WITH DUPLICATE CHECK)
# -----------------------------
if st.button("🚀 Submit Preferences"):

    if not emp_id or not name:
        st.error("❌ Enter valid Employee ID")
        st.stop()

    if len(b1_selected) != 7 or len(b2_selected) != 7:
        st.error("❌ Select exactly 7 courses in each basket")
        st.stop()

    try:
        # -----------------------------
        # CHECK EXISTING EMPLOYEE ID
        # -----------------------------
        existing_data = response_sheet.get_all_values()

        existing_emp_ids = [
            row[0].strip()
            for row in existing_data[1:]
            if row and len(row) > 0
        ]

        if emp_id in existing_emp_ids:
            st.warning("⚠️ Preferences already submitted. Only one submission allowed per faculty.")
            st.stop()

        # -----------------------------
        # INSERT DATA
        # -----------------------------
        response_sheet.append_row([
            emp_id,
            name,
            designation,
            *b1_selected,
            *b2_selected
        ])

        st.success("✅ Preferences submitted successfully!")

    except Exception as e:
        st.error(f"Error: {e}")'''
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Faculty Preference System", layout="wide")

# 🎨 FULL BACKGROUND UI
st.markdown(
"""
<style>

/* GLOBAL BACKGROUND */
.stApp {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: white;
}

/* TITLE */
h1 {
    text-align: center;
    color: white;
    font-size: 38px !important;
    font-weight: 700;
}

/* INPUT BOX */
input {
    border-radius: 10px !important;
}

/* CARD STYLE */
.block-container {
    padding-top: 2rem;
}

/* Glass effect for sections */
.css-1r6slb0, .css-1d391kg {
    background: rgba(255, 255, 255, 0.08);
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    backdrop-filter: blur(10px);
}

/* LABEL */
label {
    color: white !important;
    font-weight: 500;
}

/* BUTTON */
.stButton > button {
    background: linear-gradient(90deg, #00c6ff, #0072ff);
    color: white;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: bold;
    border: none;
    transition: 0.3s;
}

.stButton > button:hover {
    transform: scale(1.05);
    box-shadow: 0px 0px 15px rgba(0, 198, 255, 0.6);
}

/* INPUT FOCUS */
input:focus {
    border: 2px solid #00c6ff !important;
    outline: none;
}

</style>
""",
unsafe_allow_html=True
)

st.title("📊 Faculty Preference System")

SPREADSHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"

# -----------------------------
# GOOGLE AUTH
# -----------------------------
@st.cache_resource
def get_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)

client = get_client()

@st.cache_resource
def get_spreadsheet():
    return client.open_by_key(SPREADSHEET_ID)

ss = get_spreadsheet()
response_sheet = ss.get_worksheet(0)

# -----------------------------
# LOAD SHEETS
# -----------------------------
@st.cache_data(ttl=60)
def load_sheet(index):
    sheet = ss.get_worksheet(index)
    data = sheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    df.columns = df.columns.str.strip()
    return df

b1_df = load_sheet(1)
b2_df = load_sheet(2)
faculty_df = load_sheet(3)

# -----------------------------
# COURSE LIST
# -----------------------------
def get_course_list(df):
    course_col = None
    for col in df.columns:
        if "course" in col.lower():
            course_col = col
            break
    if course_col is None:
        st.error("Course column not found")
        st.stop()
    return df[course_col].dropna().astype(str).tolist()

basket1 = get_course_list(b1_df)
basket2 = get_course_list(b2_df)

# -----------------------------
# FACULTY CLEAN
# -----------------------------
faculty_df.columns = faculty_df.columns.str.strip()
faculty_df["EmpID"] = faculty_df["EmpID"].astype(str).str.strip()

# -----------------------------
# EMP ID
# -----------------------------
emp_id = st.text_input("Enter Employee ID").strip()

name = ""
designation = ""

if emp_id:
    match = faculty_df[faculty_df["EmpID"] == emp_id]

    if not match.empty:
        name = match.iloc[0]["Name"]
        designation = match.iloc[0]["Designation"]
    else:
        st.warning("❌ Employee ID not found")

st.text_input("Name", value=name, disabled=True)
st.text_input("Designation", value=designation, disabled=True)

# -----------------------------
# UI COLUMNS
# -----------------------------
col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1
# -----------------------------
with col1:
    st.subheader("📘 Basket 1")

    b1_selected = []
    available_b1 = basket1.copy()

    for i in range(7):
        choice = st.selectbox(
            f"B1 Choice {i+1}",
            ["Select"] + available_b1,
            key=f"b1_{i}"
        )

        if choice != "Select":
            b1_selected.append(choice)
            if choice in available_b1:
                available_b1.remove(choice)

# -----------------------------
# BASKET 2
# -----------------------------
with col2:
    st.subheader("📗 Basket 2")

    b2_selected = []
    available_b2 = basket2.copy()

    for i in range(7):
        choice = st.selectbox(
            f"B2 Choice {i+1}",
            ["Select"] + available_b2,
            key=f"b2_{i}"
        )

        if choice != "Select":
            b2_selected.append(choice)
            if choice in available_b2:
                available_b2.remove(choice)

# -----------------------------
# SUBMIT (ONE TIME ONLY)
# -----------------------------
if st.button("🚀 Submit Preferences"):

    if not emp_id or not name:
        st.error("❌ Enter valid Employee ID")
        st.stop()

    if len(b1_selected) != 7 or len(b2_selected) != 7:
        st.error("❌ Select exactly 7 courses in each basket")
        st.stop()

    try:
        existing_data = response_sheet.get_all_values()

        existing_emp_ids = [
            row[0].strip()
            for row in existing_data[1:]
            if row and len(row) > 0
        ]

        if emp_id in existing_emp_ids:
            st.warning("⚠️ Already submitted. Only one submission allowed per faculty.")
            st.stop()

        response_sheet.append_row([
            emp_id,
            name,
            designation,
            *b1_selected,
            *b2_selected
        ])

        st.success("✅ Preferences submitted successfully!")

    except Exception as e:
        st.error(f"Error: {e}")
