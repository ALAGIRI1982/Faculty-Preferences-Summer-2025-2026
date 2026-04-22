import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Faculty Preference System", layout="wide")
st.title("📊 Faculty Preference System (Stable Production Version)")

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
# LOAD SHEET (FIXED - NO UNHASHABLE ERROR)
# -----------------------------
@st.cache_data(ttl=60)
def load_sheet(sheet_index):
    ss = client.open_by_key(SPREADSHEET_ID)
    sheet = ss.get_worksheet(sheet_index)

    data = sheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# -----------------------------
# SHEETS
# -----------------------------
ss = client.open_by_key(SPREADSHEET_ID)
response_sheet = ss.get_worksheet(0)
basket1_sheet = ss.get_worksheet(1)
basket2_sheet = ss.get_worksheet(2)

# -----------------------------
# ENSURE USAGE COLUMN
# -----------------------------
def ensure_usage(df):
    if "Usage" not in df.columns:
        df["Usage"] = 0
    df["Usage"] = pd.to_numeric(df["Usage"], errors="coerce").fillna(0).astype(int)
    return df

# -----------------------------
# LOAD DATA (CACHED SAFE)
# -----------------------------
b1_df = ensure_usage(load_sheet(1))
b2_df = ensure_usage(load_sheet(2))

# -----------------------------
# SYSTEM STATE
# -----------------------------
existing_ids = response_sheet.col_values(1)
first_time = len(existing_ids) <= 1

# -----------------------------
# EMPLOYEE ID
# -----------------------------
emp_id = st.text_input("Enter Employee ID")

if emp_id and emp_id in existing_ids:
    st.warning("Already submitted")
    st.stop()

# -----------------------------
# GET COURSE LIST
# -----------------------------
def get_courses(df, first):
    if first:
        return df["Course"].tolist()
    else:
        return df.sort_values("Usage")["Course"].head(7).tolist()

# -----------------------------
# UI
# -----------------------------
col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1
# -----------------------------
with col1:
    st.subheader("📘 Basket 1")

    b1_list = get_courses(b1_df, first_time)
    b1_selected = []

    for i in range(7):
        choice = st.selectbox(
            f"B1 Choice {i+1}",
            ["Select"] + b1_list,
            key=f"b1_{i}"
        )

        if choice != "Select":
            b1_selected.append(choice)
            if choice in b1_list:
                b1_list.remove(choice)

# -----------------------------
# BASKET 2
# -----------------------------
with col2:
    st.subheader("📗 Basket 2")

    b2_list = get_courses(b2_df, first_time)
    b2_selected = []

    for i in range(7):
        choice = st.selectbox(
            f"B2 Choice {i+1}",
            ["Select"] + b2_list,
            key=f"b2_{i}"
        )

        if choice != "Select":
            b2_selected.append(choice)
            if choice in b2_list:
                b2_list.remove(choice)

# -----------------------------
# UPDATE USAGE (SAFE WRITE)
# -----------------------------
def update_usage(sheet, df, selected):
    for course in selected:
        try:
            idx = df.index[df["Course"] == course][0]
            new_val = int(df.loc[idx, "Usage"]) + 1
            df.loc[idx, "Usage"] = new_val

            cell = sheet.find(course)
            row = cell.row
            col = df.columns.get_loc("Usage") + 1

            sheet.update_cell(row, col, new_val)

        except Exception as e:
            st.error(f"Error updating {course}: {e}")

# -----------------------------
# SUBMIT
# -----------------------------
if st.button("🚀 Submit Preferences"):

    if len(b1_selected) != 7 or len(b2_selected) != 7:
        st.error("Select exactly 7 courses in each basket")
        st.stop()

    try:
        update_usage(basket1_sheet, b1_df, b1_selected)
        update_usage(basket2_sheet, b2_df, b2_selected)

        response_sheet.append_row([
            emp_id,
            *b1_selected,
            *b2_selected
        ])

        st.success("✅ Submitted Successfully")

        st.cache_data.clear()

    except Exception as e:
        st.error(f"Error: {e}")
