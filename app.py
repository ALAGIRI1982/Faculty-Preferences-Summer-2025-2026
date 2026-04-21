import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.title("Faculty Preferences for Summer 2025-2026")

# -----------------------------
# GOOGLE SHEETS CONNECTION
# -----------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)

SHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"

# ✅ OPEN SPREADSHEET
spreadsheet = client.open_by_key(SHEET_ID)

# ✅ CORRECT SHEETS
response_sheet = spreadsheet.worksheet("Responses")
basket1_sheet = spreadsheet.worksheet("Sheet1")
basket2_sheet = spreadsheet.worksheet("Sheet2")

# -----------------------------
# CREATE HEADER (SAFE)
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
# LOAD COURSES FROM GOOGLE SHEETS
# -----------------------------
b1_df = pd.DataFrame(basket1_sheet.get_all_records())
b2_df = pd.DataFrame(basket2_sheet.get_all_records())

# Clean column names (important)
b1_df.columns = b1_df.columns.str.strip()
b2_df.columns = b2_df.columns.str.strip()

# Validate structure
if "Course" not in b1_df.columns or "Count" not in b1_df.columns:
    st.error("Sheet1 must contain columns: Course, Count")
    st.stop()

if "Course" not in b2_df.columns or "Count" not in b2_df.columns:
    st.error("Sheet2 must contain columns: Course, Count")
    st.stop()

# Filter available courses
basket1 = b1_df[b1_df["Count"] > 0]["Course"].tolist()
basket2 = b2_df[b2_df["Count"] > 0]["Course"].tolist()

# -----------------------------
# LOAD EMPLOYEE DATA
# -----------------------------
employees = pd.read_excel("employees.xlsx")

# -----------------------------
# EMPLOYEE INPUT
# -----------------------------
emp_id = st.text_input("Enter Employee ID")

name = ""
designation = ""

if emp_id:
    emp_row = employees[employees["EmpID"].astype(str) == emp_id]
    if not emp_row.empty:
        name = emp_row.iloc[0]["Name"]
        designation = emp_row.iloc[0]["Designation"]
        st.success("Employee Found")
        st.write("Name:", name)
        st.write("Designation:", designation)
    else:
        st.error("Invalid Employee ID")

# -----------------------------
# DUPLICATE CHECK
# -----------------------------
existing_ids = response_sheet.col_values(1)

if emp_id and emp_id in existing_ids:
    st.warning("You have already submitted your preferences")
    st.stop()

# -----------------------------
# DECREMENT FUNCTION
# -----------------------------
def decrement(sheet_obj, course):
    try:
        cell = sheet_obj.find(course)
        row = cell.row
        count = int(sheet_obj.cell(row, 2).value)

        if count <= 0:
            return False

        sheet_obj.update_cell(row, 2, count - 1)
        return True
    except:
        return False

# -----------------------------
# UI
# -----------------------------
if name != "":

    # -------- Basket 1 --------
    st.subheader("Basket 1 Preferences")
    basket1_pref = []
    available_courses = basket1.copy()

    for i in range(1, 8):
        choice = st.selectbox(
            f"BS1P{i}",
            ["Select Course"] + available_courses,
            key=f"b1{i}"
        )
        if choice != "Select Course":
            basket1_pref.append(choice)
            if choice in available_courses:
                available_courses.remove(choice)

    # -------- Basket 2 --------
    st.subheader("Basket 2 Preferences")
    basket2_pref = []
    available_courses2 = basket2.copy()

    for i in range(1, 8):
        choice = st.selectbox(
            f"BS2P{i}",
            ["Select Course"] + available_courses2,
            key=f"b2{i}"
        )
        if choice != "Select Course":
            basket2_pref.append(choice)
            if choice in available_courses2:
                available_courses2.remove(choice)

    # -----------------------------
    # SUBMIT
    # -----------------------------
    if st.button("Submit Preference"):

        if len(basket1_pref) != 7:
            st.error("Please select 7 courses in Basket 1")
            st.stop()

        if len(basket2_pref) != 7:
            st.error("Please select 7 courses in Basket 2")
            st.stop()

        # Decrement Basket 1
        for course in basket1_pref:
            if not decrement(basket1_sheet, course):
                st.error(f"{course} is full in Basket 1")
                st.stop()

        # Decrement Basket 2
        for course in basket2_pref:
            if not decrement(basket2_sheet, course):
                st.error(f"{course} is full in Basket 2")
                st.stop()

        # Save Response
        row = [
            emp_id,
            name,
            designation,
            *basket1_pref,
            *basket2_pref
        ]

        response_sheet.append_row(row)

        st.success("Preference Submitted Successfully")
