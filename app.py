'''import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

st.title("Faculty Preferences System (Stable Version)")

# -----------------------------
# GOOGLE CLIENT
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


@st.cache_resource
def get_sheet():
    client = get_client()
    return client.open_by_key("1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg")


spreadsheet = get_sheet()

# -----------------------------
# SAFE INDEX-BASED SHEETS
# -----------------------------
response_sheet = spreadsheet.get_worksheet(0)
basket1_sheet  = spreadsheet.get_worksheet(1)
basket2_sheet  = spreadsheet.get_worksheet(2)

# -----------------------------
# CACHE EXISTING IDS (FIX API SPAM)
# -----------------------------
@st.cache_data(ttl=60)
def get_existing_ids():
    return response_sheet.col_values(1)

existing_ids = get_existing_ids()

# -----------------------------
# SAFE COURSE LOADER
# -----------------------------
@st.cache_data(ttl=60)
def load_courses(index):
    sheet = spreadsheet.get_worksheet(index)
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip()
    return df

b1_df = load_courses(1)
b2_df = load_courses(2)

basket1 = b1_df[b1_df["Count"] > 0]["Course"].tolist()
basket2 = b2_df[b2_df["Count"] > 0]["Course"].tolist()

# -----------------------------
# EMPLOYEE INPUT
# -----------------------------
emp_id = st.text_input("Employee ID")

# -----------------------------
# SUBMISSION LOCK (CRITICAL FIX)
# -----------------------------
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# prevent rerun double submit
if st.session_state.submitted:
    st.success("Already submitted in this session.")
    st.stop()

# -----------------------------
# DUPLICATE CHECK
# -----------------------------
if emp_id and emp_id in existing_ids:
    st.warning("Already submitted in Google Sheet")
    st.stop()

# -----------------------------
# EMP DATA (OPTIONAL FILE)
# -----------------------------
try:
    employees = pd.read_excel("employees.xlsx")
except:
    employees = pd.DataFrame()

name, designation = "", ""

if emp_id and not employees.empty:
    emp_row = employees[employees["EmpID"].astype(str) == emp_id]

    if not emp_row.empty:
        name = emp_row.iloc[0]["Name"]
        designation = emp_row.iloc[0]["Designation"]
        st.success("Employee Found")

# -----------------------------
# UI SELECTION
# -----------------------------
if emp_id:

    st.subheader("Basket 1")
    b1_temp = basket1.copy()
    basket1_pref = []

    for i in range(7):
        choice = st.selectbox(
            f"B1P{i+1}",
            ["Select"] + b1_temp,
            key=f"b1_{i}"
        )
        if choice != "Select":
            basket1_pref.append(choice)
            if choice in b1_temp:
                b1_temp.remove(choice)

    st.subheader("Basket 2")
    b2_temp = basket2.copy()
    basket2_pref = []

    for i in range(7):
        choice = st.selectbox(
            f"B2P{i+1}",
            ["Select"] + b2_temp,
            key=f"b2_{i}"
        )
        if choice != "Select":
            basket2_pref.append(choice)
            if choice in b2_temp:
                b2_temp.remove(choice)

# -----------------------------
# SAFE DECREMENT WITH RETRY
# -----------------------------
def safe_decrement(sheet, course):
    try:
        cell = sheet.find(course)
        row = cell.row

        count = int(sheet.cell(row, 2).value)

        if count <= 0:
            return False

        sheet.update_cell(row, 2, count - 1)
        return True

    except Exception:
        time.sleep(1)
        return False

# -----------------------------
# SUBMIT (CRASH PROOF)
# -----------------------------
if st.button("Submit"):

    if len(basket1_pref) != 7 or len(basket2_pref) != 7:
        st.error("Select all 7 preferences")
        st.stop()

    try:
        # LOCK (prevents rerun double submit)
        st.session_state.submitted = True

        # decrement basket 1
        for c in basket1_pref:
            if not safe_decrement(basket1_sheet, c):
                st.session_state.submitted = False
                st.error(f"{c} full in Basket 1")
                st.stop()

        # decrement basket 2
        for c in basket2_pref:
            if not safe_decrement(basket2_sheet, c):
                st.session_state.submitted = False
                st.error(f"{c} full in Basket 2")
                st.stop()

        # append row
        response_sheet.append_row([
            emp_id, name, designation,
            *basket1_pref,
            *basket2_pref
        ])

        # refresh cache
        st.cache_data.clear()

        st.success("Submitted Successfully")

    except Exception as e:
        st.session_state.submitted = False
        st.error(f"Submission failed: {e}")'''
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Faculty Preference System", layout="wide")

st.title("📊 Faculty Preferences for Summer 2025-2026")

# -----------------------------
# GOOGLE CONNECTION
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


@st.cache_resource
def get_spreadsheet():
    client = get_client()
    return client.open_by_key("1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg")


spreadsheet = get_spreadsheet()

# -----------------------------
# SHEETS (SAFE INDEX BASED)
# -----------------------------
response_sheet = spreadsheet.get_worksheet(0)
basket1_sheet  = spreadsheet.get_worksheet(1)
basket2_sheet  = spreadsheet.get_worksheet(2)

# -----------------------------
# CACHE EXISTING IDS (PREVENT API OVERLOAD)
# -----------------------------
@st.cache_data(ttl=60)
def get_existing_ids():
    return response_sheet.col_values(1)

existing_ids = get_existing_ids()

# -----------------------------
# LOAD COURSE DATA
# -----------------------------
@st.cache_data(ttl=60)
def load_courses(index):
    sheet = spreadsheet.get_worksheet(index)
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip()
    return df

b1_df = load_courses(1)
b2_df = load_courses(2)

basket1 = b1_df[b1_df["Count"] > 0]["Course"].tolist()
basket2 = b2_df[b2_df["Count"] > 0]["Course"].tolist()

# -----------------------------
# EMPLOYEE INPUT
# -----------------------------
emp_id = st.text_input("Enter Employee ID")

# -----------------------------
# SESSION LOCK (PREVENT DOUBLE SUBMIT)
# -----------------------------
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if st.session_state.submitted:
    st.success("Already submitted in this session.")
    st.stop()

# -----------------------------
# EMP DATA (OPTIONAL)
# -----------------------------
name, designation = "", ""

try:
    employees = pd.read_excel("employees.xlsx")

    if emp_id:
        emp_row = employees[employees["EmpID"].astype(str) == emp_id]

        if not emp_row.empty:
            name = emp_row.iloc[0]["Name"]
            designation = emp_row.iloc[0]["Designation"]
            st.success("Employee Found")

except:
    pass

# -----------------------------
# DUPLICATE CHECK
# -----------------------------
if emp_id and emp_id in existing_ids:
    st.warning("You have already submitted preferences")
    st.stop()

# -----------------------------
# SIDE BY SIDE UI (FIXED)
# -----------------------------
col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1 (LEFT)
# -----------------------------
with col1:
    st.subheader("📘 Basket 1")

    basket1_pref = []
    temp1 = basket1.copy()

    max_b1 = min(7, len(basket1))

    for i in range(max_b1):
        choice = st.selectbox(
            f"BS1P{i+1}",
            ["Select Course"] + temp1,
            key=f"b1_{i}"
        )

        if choice != "Select Course":
            basket1_pref.append(choice)
            if choice in temp1:
                temp1.remove(choice)

# -----------------------------
# BASKET 2 (RIGHT)
# -----------------------------
with col2:
    st.subheader("📗 Basket 2")

    basket2_pref = []
    temp2 = basket2.copy()

    max_b2 = min(7, len(basket2))

    for i in range(max_b2):
        choice = st.selectbox(
            f"BS2P{i+1}",
            ["Select Course"] + temp2,
            key=f"b2_{i}"
        )

        if choice != "Select Course":
            basket2_pref.append(choice)
            if choice in temp2:
                temp2.remove(choice)

# -----------------------------
# SAFE DECREMENT
# -----------------------------
def safe_decrement(sheet, course):
    try:
        cell = sheet.find(course)
        row = cell.row

        count = int(sheet.cell(row, 2).value)

        if count <= 0:
            return False

        sheet.update_cell(row, 2, count - 1)
        return True

    except Exception:
        time.sleep(1)
        return False

# -----------------------------
# SUBMIT BUTTON
# -----------------------------
if st.button("🚀 Submit Preferences"):

    if len(basket1_pref) != max_b1:
        st.error(f"Select {max_b1} courses in Basket 1")
        st.stop()

    if len(basket2_pref) != max_b2:
        st.error(f"Select {max_b2} courses in Basket 2")
        st.stop()

    try:
        st.session_state.submitted = True

        # update basket 1
        for c in basket1_pref:
            if not safe_decrement(basket1_sheet, c):
                st.session_state.submitted = False
                st.error(f"{c} full in Basket 1")
                st.stop()

        # update basket 2
        for c in basket2_pref:
            if not safe_decrement(basket2_sheet, c):
                st.session_state.submitted = False
                st.error(f"{c} full in Basket 2")
                st.stop()

        # save response
        response_sheet.append_row([
            emp_id,
            name,
            designation,
            *basket1_pref,
            *basket2_pref
        ])

        st.cache_data.clear()

        st.success("✅ Preferences Submitted Successfully")

    except Exception as e:
        st.session_state.submitted = False
        st.error(f"Error: {e}")
