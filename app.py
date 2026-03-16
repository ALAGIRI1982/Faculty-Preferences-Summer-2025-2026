import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Faculty Preference System", layout="wide")

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
sheet = client.open_by_key(SHEET_ID).sheet1

# -----------------------------
# HEADER CREATION
# -----------------------------
headers = [
    "EmpID","Name","Designation",
    "BS1P1","BS1P2","BS1P3","BS1P4","BS1P5","BS1P6","BS1P7",
    "BS2P1","BS2P2","BS2P3","BS2P4","BS2P5","BS2P6","BS2P7"
]

if len(sheet.row_values(1)) == 0:
    sheet.update('A1:Q1', [headers])

# -----------------------------
# LOAD COURSE DATA
# -----------------------------
courses = pd.read_excel("courses.xlsx", sheet_name=None)

basket1 = courses["Sheet1"]["Course"].dropna().tolist()
basket2 = courses["Sheet2"]["Course"].dropna().tolist()

# -----------------------------
# LOAD EMPLOYEE DATA
# -----------------------------
employees = pd.read_excel("employees.xlsx")

# -----------------------------
# EMPLOYEE LOGIN
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

        c1, c2 = st.columns(2)

        with c1:
            st.write("Name:", name)

        with c2:
            st.write("Designation:", designation)

        # duplicate check
        existing_ids = sheet.col_values(1)

        if emp_id in existing_ids:
            st.warning("You have already submitted your preferences")
            st.stop()

    else:
        st.error("Invalid Employee ID")

# -----------------------------
# PREFERENCE PANELS
# -----------------------------
if name != "":

    col1, col2 = st.columns(2)

    # -----------------------------
    # BASKET 1
    # -----------------------------
    with col1:

        st.subheader("Basket 1 Preferences")

        basket1_pref = []
        available_courses = basket1.copy()

        for i in range(1,8):

            choice = st.selectbox(
                f"BS1P{i}",
                ["Select Course"] + available_courses,
                key=f"b1{i}"
            )

            if choice != "Select Course":
                basket1_pref.append(choice)

                if choice in available_courses:
                    available_courses.remove(choice)

        st.info(f"Selected: {len(basket1_pref)} / 7")

    # -----------------------------
    # BASKET 2
    # -----------------------------
    with col2:

        st.subheader("Basket 2 Preferences")

        basket2_pref = []
        available_courses2 = basket2.copy()

        for i in range(1,8):

            choice = st.selectbox(
                f"BS2P{i}",
                ["Select Course"] + available_courses2,
                key=f"b2{i}"
            )

            if choice != "Select Course":
                basket2_pref.append(choice)

                if choice in available_courses2:
                    available_courses2.remove(choice)

        st.info(f"Selected: {len(basket2_pref)} / 7")

# -----------------------------
# SUBMIT
# -----------------------------
    st.markdown("---")

    if st.button("Submit Preference"):

        if len(basket1_pref) != 7:
            st.error("Please select 7 courses in Basket 1")
            st.stop()

        if len(basket2_pref) != 7:
            st.error("Please select 7 courses in Basket 2")
            st.stop()

        row = [
            emp_id,
            name,
            designation,
            *basket1_pref,
            *basket2_pref
        ]

        sheet.append_row(row)

        st.success("Preference Submitted Successfully")
