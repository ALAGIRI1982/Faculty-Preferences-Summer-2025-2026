import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Faculty Preference System", layout="wide")
st.title("📊 Faculty Preference System (No Duplicate Selection)")

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
# LOAD SHEETS
# -----------------------------
@st.cache_data(ttl=60)
def load_sheet(index):
    sheet = ss.get_worksheet(index)
    data = sheet.get_all_values()
    return pd.DataFrame(data[1:], columns=data[0])

b1_df = load_sheet(1)
b2_df = load_sheet(2)

basket1 = b1_df["Course"].tolist()
basket2 = b2_df["Course"].tolist()

# -----------------------------
# EMP ID
# -----------------------------
emp_id = st.text_input("Enter Employee ID")

# -----------------------------
# UI
# -----------------------------
col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1 (NO DUPLICATES)
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
# BASKET 2 (NO DUPLICATES)
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
# SUBMIT
# -----------------------------
if st.button("🚀 Submit Preferences"):

    if len(b1_selected) != 7 or len(b2_selected) != 7:
        st.error("Select exactly 7 unique courses in each basket")
        st.stop()

    try:
        response_sheet.append_row([
            emp_id,
            *b1_selected,
            *b2_selected
        ])

        st.success("✅ Submitted Successfully")

    except Exception as e:
        st.error(f"Error: {e}")
