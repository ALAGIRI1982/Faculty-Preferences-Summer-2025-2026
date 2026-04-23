import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# PAGE CONFIG
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

@st.cache_resource
def get_spreadsheet():
    return client.open_by_key(SPREADSHEET_ID)

ss = get_spreadsheet()

# -----------------------------
# LOAD SHEETS
# -----------------------------
@st.cache_data(ttl=60)
def load_sheet(sheet_name):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()
    return pd.DataFrame(data[1:], columns=data[0])

# -----------------------------
# STRICT VALIDATION (IMPORTANT)
# -----------------------------
def ensure_usage(df):
    if "Usage" not in df.columns:
        df["Usage"] = 0

    if "Max" not in df.columns:
        st.error("❌ 'Max' column missing in sheet")
        st.stop()

    df["Usage"] = pd.to_numeric(df["Usage"], errors="coerce").fillna(0).astype(int)
    df["Max"] = pd.to_numeric(df["Max"], errors="coerce")

    # 🔥 CRITICAL FIX
    if df["Max"].isnull().any() or (df["Max"] <= 0).any():
        st.error("❌ Max must be greater than 0 for ALL courses in sheet")
        st.stop()

    df["Max"] = df["Max"].astype(int)

    return df

b1_df = ensure_usage(load_sheet("Basket1"))
b2_df = ensure_usage(load_sheet("Basket2"))

# -----------------------------
# EMPLOYEES
# -----------------------------
@st.cache_data(ttl=60)
def load_employees():
    sheet = ss.worksheet("Faculty List")
    data = sheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])

    df.columns = df.columns.str.strip()
    df["EmpID"] = df["EmpID"].astype(str).str.strip()
    return df

employees = load_employees()

# -----------------------------
# SESSION STATE
# -----------------------------
if "name" not in st.session_state:
    st.session_state.name = None
    st.session_state.designation = None

# -----------------------------
# EMP INPUT
# -----------------------------
emp_id = st.text_input("Enter Employee ID")

if emp_id:
    emp_id = str(emp_id).strip()
    emp_row = employees[employees["EmpID"] == emp_id]

    if not emp_row.empty:
        st.session_state.name = emp_row.iloc[0]["Name"]
        st.session_state.designation = emp_row.iloc[0]["Designation"]

        st.success("Employee Found ✅")
        st.write("Name:", st.session_state.name)
        st.write("Designation:", st.session_state.designation)
    else:
        st.warning("Employee ID not found ❌")

# -----------------------------
# DUPLICATE CHECK
# -----------------------------
response_sheet = ss.worksheet("Responses")
existing_ids = [str(x).strip() for x in response_sheet.col_values(1)]

if emp_id and emp_id in existing_ids:
    st.error("❌ You have already submitted")
    st.stop()

# -----------------------------
# COURSE LIST (ONLY NAMES)
# -----------------------------
b1_courses = b1_df["Course"].dropna().astype(str).tolist()
b2_courses = b2_df["Course"].dropna().astype(str).tolist()

col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1
# -----------------------------
with col1:
    st.subheader("📘 Basket 1")

    b1_selected = st.multiselect(
        "Select exactly 7 courses",
        b1_courses,
        max_selections=7
    )

    st.write(f"Selected: {len(b1_selected)} / 7")

    # FULL warning
    for c in b1_selected:
        row = b1_df[b1_df["Course"] == c].iloc[0]
        if row["Usage"] >= row["Max"]:
            st.error(f"⚠ {c} is FULL!")

# -----------------------------
# BASKET 2
# -----------------------------
with col2:
    st.subheader("📗 Basket 2")

    b2_selected = st.multiselect(
        "Select exactly 7 courses",
        b2_courses,
        max_selections=7
    )

    st.write(f"Selected: {len(b2_selected)} / 7")

    for c in b2_selected:
        row = b2_df[b2_df["Course"] == c].iloc[0]
        if row["Usage"] >= row["Max"]:
            st.error(f"⚠ {c} is FULL!")

# -----------------------------
# UPDATE USAGE
# -----------------------------
def update_usage(sheet_name, selected):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()

    headers = data[0]
    rows = data[1:]

    c_idx = headers.index("Course")
    u_idx = headers.index("Usage")

    usage_map = {}

    for r in rows:
        usage_map[r[c_idx]] = int(r[u_idx]) if r[u_idx] else 0

    for c in selected:
        usage_map[c] += 1

    updated_col = [[usage_map[r[c_idx]]] for r in rows]

    col_letter = chr(65 + u_idx)
    sheet.update(f"{col_letter}2:{col_letter}{len(rows)+1}", updated_col)

# -----------------------------
# SUBMIT
# -----------------------------
if st.button("🚀 Submit Preferences"):

    if st.session_state.name is None:
        st.error("❌ Enter valid Employee ID first")
        st.stop()

    if len(b1_selected) != 7 or len(b2_selected) != 7:
        st.error("❌ Select exactly 7 courses in each basket")
        st.stop()

    try:
        update_usage("Basket1", b1_selected)
        update_usage("Basket2", b2_selected)

        response_sheet.append_row([
            emp_id,
            st.session_state.name,
            st.session_state.designation,
            *b1_selected,
            *b2_selected
        ])

        st.success("✅ Submitted Successfully")

        st.cache_data.clear()
        st.cache_resource.clear()

    except Exception as e:
        st.error(f"Error: {e}")
