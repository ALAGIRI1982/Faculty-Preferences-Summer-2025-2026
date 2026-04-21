import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.title("Faculty Preferences for Summer 2025-2026")

# -----------------------------
# GOOGLE CLIENT (SAFE)
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
# SAFE SHEET ACCESS (FIXED)
# -----------------------------
response_sheet = spreadsheet.get_worksheet(0)
basket1_sheet  = spreadsheet.get_worksheet(1)
basket2_sheet  = spreadsheet.get_worksheet(2)

# Debug
st.write("Available sheets:")
st.write([ws.title for ws in spreadsheet.worksheets()])

# -----------------------------
# HEADER CHECK
# -----------------------------
headers = [
    "EmpID", "Name", "Designation",
    "BS1P1","BS1P2","BS1P3","BS1P4","BS1P5","BS1P6","BS1P7",
    "BS2P1","BS2P2","BS2P3","BS2P4","BS2P5","BS2P6","BS2P7"
]

try:
    first_row = response_sheet.row_values(1)
except:
    first_row = []

if first_row != headers:
    response_sheet.update('A1:Q1', [headers])

# -----------------------------
# SAFE DATA LOADER (FIXED)
# -----------------------------
@st.cache_data
def load_courses(sheet_index):
    sheet = spreadsheet.get_worksheet(sheet_index)
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip()
    return df

b1_df = load_courses(1)
b2_df = load_courses(2)

if "Course" not in b1_df.columns or "Count" not in b1_df.columns:
    st.error("Sheet1 must contain Course, Count")
    st.stop()

if "Course" not in b2_df.columns or "Count" not in b2_df.columns:
    st.error("Sheet2 must contain Course, Count")
    st.stop()

basket1 = b1_df[b1_df["Count"] > 0]["Course"].tolist()
basket2 = b2_df[b2_df["Count"] > 0]["Course"].tolist()

# -----------------------------
# EMP DATA
# -----------------------------
employees = pd.read_excel("employees.xlsx")

emp_id = st.text_input("Enter Employee ID")

name = ""
designation = ""

if emp_id:
    emp_row = employees[employees["EmpID"].astype(str) == emp_id]

    if not emp_row.empty:
        name = emp_row.iloc[0]["Name"]
        designation = emp_row.iloc[0]["Designation"]
        st.success("Employee Found")
    else:
        st.error("Invalid Employee ID")

# -----------------------------
# DUPLICATE CHECK
# -----------------------------
existing_ids = response_sheet.col_values(1)

if emp_id and emp_id in existing_ids:
    st.warning("Already submitted")
    st.stop()

# -----------------------------
# DECREMENT SAFE
# -----------------------------
def decrement(sheet, course):
    try:
        cell = sheet.find(course)
        row = cell.row
        count = int(sheet.cell(row, 2).value)

        if count <= 0:
            return False

        sheet.update_cell(row, 2, count - 1)
        return True
    except:
        return False

# -----------------------------
# UI
# -----------------------------
if name:

    st.subheader("Basket 1 Preferences")
    basket1_pref = []
    temp1 = basket1.copy()

    for i in range(1, 8):
        choice = st.selectbox(
            f"BS1P{i}",
            ["Select"] + temp1,
            key=f"b1{i}"
        )

        if choice != "Select":
            basket1_pref.append(choice)
            if choice in temp1:
                temp1.remove(choice)

    st.subheader("Basket 2 Preferences")
    basket2_pref = []
    temp2 = basket2.copy()

    for i in range(1, 8):
        choice = st.selectbox(
            f"BS2P{i}",
            ["Select"] + temp2,
            key=f"b2{i}"
        )

        if choice != "Select":
            basket2_pref.append(choice)
            if choice in temp2:
                temp2.remove(choice)

    if st.button("Submit Preference"):

        if len(basket1_pref) != 7 or len(basket2_pref) != 7:
            st.error("Select all 7 preferences")
            st.stop()

        for c in basket1_pref:
            if not decrement(basket1_sheet, c):
                st.error(f"{c} full in Basket 1")
                st.stop()

        for c in basket2_pref:
            if not decrement(basket2_sheet, c):
                st.error(f"{c} full in Basket 2")
                st.stop()

        response_sheet.append_row([
            emp_id, name, designation,
            *basket1_pref, *basket2_pref
        ])

        st.cache_data.clear()
        st.success("Submitted Successfully")
