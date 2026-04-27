'''import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Faculty Preference System ", layout="wide")

# -----------------------------
# 🌈 UI
# -----------------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #ff6ec4, #7873f5, #4facfe, #43e97b, #f9d423);
    background-size: 300% 300%;
    animation: gradientMove 12s ease infinite;
}
@keyframes gradientMove {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}
.block-container {
    background: rgba(255,255,255,0.92);
    padding: 25px;
    border-radius: 18px;
}
.title {
    text-align:center;
    font-size:40px;
    font-weight:800;
}
.basket1 {
    background: linear-gradient(90deg, #2563eb, #3b82f6);
    padding:10px;
    border-radius:10px;
    color:white;
    font-weight:bold;
}
.basket2 {
    background: linear-gradient(90deg, #ec4899, #f43f5e);
    padding:10px;
    border-radius:10px;
    color:white;
    font-weight:bold;
}
.green { color:#16a34a; font-weight:600; }
.red { color:#dc2626; font-weight:600; }
.stButton>button {
    background: linear-gradient(90deg,#7c3aed,#ec4899);
    color:white;
    font-weight:bold;
    border-radius:10px;
    height:50px;
    width:100%;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>🎓 Faculty Course Preference System Fall 2026-2027</div>", unsafe_allow_html=True)

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
# LOAD DATA
# -----------------------------
@st.cache_data(ttl=60)
def load_sheet(name):
    sheet = ss.worksheet(name)
    data = sheet.get_all_values()
    return pd.DataFrame(data[1:], columns=data[0])

def clean_df(df):
    df["Usage"] = pd.to_numeric(df.get("Usage", 0), errors="coerce").fillna(0).astype(int)
    df["Max"] = pd.to_numeric(df.get("Max", 0), errors="coerce").fillna(0).astype(int)

    if (df["Max"] <= 0).any():
        st.error("Max must be > 0")
        st.stop()

    return df

b1_df = clean_df(load_sheet("Basket1"))
b2_df = clean_df(load_sheet("Basket2"))

# -----------------------------
# EMPLOYEE DATA
# -----------------------------
@st.cache_data(ttl=60)
def load_employees():
    sheet = ss.worksheet("Faculty List")
    data = sheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
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
    emp_id = emp_id.strip()
    row = employees[employees["EmpID"] == emp_id]

    if not row.empty:
        st.session_state.name = row.iloc[0]["Name"]
        st.session_state.designation = row.iloc[0]["Designation"]

        st.success("Employee Found")
        st.write("Name:", st.session_state.name)
        st.write("Designation:", st.session_state.designation)
    else:
        st.warning("Invalid Employee ID")

# -----------------------------
# DUPLICATE CHECK
# -----------------------------
response_sheet = ss.worksheet("Responses")
existing_ids = [str(x).strip() for x in response_sheet.col_values(1)]

if emp_id and emp_id in existing_ids:
    st.error("Already submitted")
    st.stop()

# -----------------------------
# LEGEND
# -----------------------------
st.markdown("""
<div style='text-align:center; font-size:18px; font-weight:700; margin:10px;'>
🟢 Low Preferred Course &nbsp;&nbsp;&nbsp; 🔴 High Preferred Course
</div>
""", unsafe_allow_html=True)

# -----------------------------
# COURSE LIST (ALL COURSES)
# -----------------------------
b1_courses = b1_df["Course"].dropna().tolist()
b2_courses = b2_df["Course"].dropna().tolist()

col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1
# -----------------------------
with col1:
    st.markdown("<div class='basket1'>📘 Basket 1</div>", unsafe_allow_html=True)

    b1_selected = st.multiselect("Select exactly 7 courses", b1_courses)
    st.write(f"Selected: {len(b1_selected)} / 7")

    if len(b1_selected) > 7:
        st.error("Only 7 allowed")

    for c in b1_selected[:7]:
        row = b1_df[b1_df["Course"] == c].iloc[0]

        if row["Usage"] < row["Max"]:
            st.markdown(f"<div class='green'>🟢 {c}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='red'>🔴 {c}</div>", unsafe_allow_html=True)

# -----------------------------
# BASKET 2
# -----------------------------
with col2:
    st.markdown("<div class='basket2'>📗 Basket 2</div>", unsafe_allow_html=True)

    b2_selected = st.multiselect("Select exactly 7 courses", b2_courses)
    st.write(f"Selected: {len(b2_selected)} / 7")

    if len(b2_selected) > 7:
        st.error("Only 7 allowed")

    for c in b2_selected[:7]:
        row = b2_df[b2_df["Course"] == c].iloc[0]

        if row["Usage"] < row["Max"]:
            st.markdown(f"<div class='green'>🟢 {c}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='red'>🔴 {c}</div>", unsafe_allow_html=True)

# -----------------------------
# UPDATE USAGE (SAFE)
# -----------------------------
def update_usage(sheet_name, selected, df):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()

    headers = data[0]
    rows = data[1:]

    c_idx = headers.index("Course")
    u_idx = headers.index("Usage")

    usage = {r[c_idx]: int(r[u_idx]) if r[u_idx] else 0 for r in rows}
    max_map = dict(zip(df["Course"], df["Max"]))

    for c in selected[:7]:
        if usage[c] < max_map[c]:  # prevent overflow
            usage[c] += 1

    updated = [[usage[r[c_idx]]] for r in rows]

    col_letter = chr(65 + u_idx)
    sheet.update(f"{col_letter}2:{col_letter}{len(rows)+1}", updated)

# -----------------------------
# SUBMIT
# -----------------------------
if st.button("🚀 Submit Preferences"):

    if st.session_state.name is None:
        st.error("Enter valid Employee ID")
        st.stop()

    if len(b1_selected) != 7 or len(b2_selected) != 7:
        st.error("Select exactly 7 courses in each basket")
        st.stop()

    try:
        update_usage("Basket1", b1_selected, b1_df)
        update_usage("Basket2", b2_selected, b2_df)

        response_sheet.append_row([
            emp_id,
            st.session_state.name,
            st.session_state.designation,
            *b1_selected[:7],
            *b2_selected[:7]
        ])

        st.success("✅ Submitted Successfully")

        st.cache_data.clear()
        st.cache_resource.clear()

    except Exception as e:
        st.error(str(e))'''
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Faculty Preference System", layout="wide")

# -----------------------------
# 🌈 UI
# -----------------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #ff6ec4, #7873f5, #4facfe, #43e97b, #f9d423);
    background-size: 300% 300%;
    animation: gradientMove 12s ease infinite;
}
@keyframes gradientMove {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}
.block-container {
    background: rgba(255,255,255,0.92);
    padding: 25px;
    border-radius: 18px;
}
.title {
    text-align:center;
    font-size:40px;
    font-weight:800;
}
.basket1 {
    background: linear-gradient(90deg, #2563eb, #3b82f6);
    padding:10px;
    border-radius:10px;
    color:white;
    font-weight:bold;
}
.basket2 {
    background: linear-gradient(90deg, #ec4899, #f43f5e);
    padding:10px;
    border-radius:10px;
    color:white;
    font-weight:bold;
}
.green { color:#16a34a; font-weight:600; }
.red { color:#dc2626; font-weight:600; }
.stButton>button {
    background: linear-gradient(90deg,#7c3aed,#ec4899);
    color:white;
    font-weight:bold;
    border-radius:10px;
    height:50px;
    width:100%;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>🎓 Faculty Course Preference System Fall 2026-2027</div>", unsafe_allow_html=True)

# -----------------------------
# SUCCESS PLACEHOLDER (TOP)
# -----------------------------
success_placeholder = st.empty()

# -----------------------------
# GOOGLE SHEETS CONFIG
# -----------------------------
SPREADSHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"

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
# LOAD DATA
# -----------------------------
@st.cache_data(ttl=60)
def load_sheet(name):
    sheet = ss.worksheet(name)
    data = sheet.get_all_values()
    return pd.DataFrame(data[1:], columns=data[0])

def clean_df(df):
    df["Usage"] = pd.to_numeric(df.get("Usage", 0), errors="coerce").fillna(0).astype(int)
    df["Max"] = pd.to_numeric(df.get("Max", 0), errors="coerce").fillna(0).astype(int)

    if (df["Max"] <= 0).any():
        st.error("Max must be > 0")
        st.stop()

    return df

b1_df = clean_df(load_sheet("Basket1"))
b2_df = clean_df(load_sheet("Basket2"))

# -----------------------------
# EMPLOYEE DATA
# -----------------------------
@st.cache_data(ttl=60)
def load_employees():
    sheet = ss.worksheet("Faculty List")
    data = sheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    df["EmpID"] = df["EmpID"].astype(str).str.strip()
    return df

employees = load_employees()

# -----------------------------
# SESSION STATE
# -----------------------------
if "name" not in st.session_state:
    st.session_state.name = None
    st.session_state.designation = None
    st.session_state.submitted = False

# -----------------------------
# STOP UI IF SUBMITTED
# -----------------------------
if st.session_state.submitted:
    success_placeholder.markdown("""
    <div style="
        display:flex;
        justify-content:center;
        align-items:center;
        height:400px;
    ">
        <div style="
            background:#16a34a;
            color:white;
            padding:30px 60px;
            border-radius:15px;
            font-size:24px;
            font-weight:bold;
            box-shadow:0 4px 20px rgba(0,0,0,0.3);
        ">
            ✅ Submitted Successfully
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# -----------------------------
# EMP INPUT
# -----------------------------
emp_id = st.text_input("Enter Employee ID")

if emp_id:
    emp_id = emp_id.strip()
    row = employees[employees["EmpID"] == emp_id]

    if not row.empty:
        st.session_state.name = row.iloc[0]["Name"]
        st.session_state.designation = row.iloc[0]["Designation"]

        st.success("Employee Found")
        st.write("Name:", st.session_state.name)
        st.write("Designation:", st.session_state.designation)
    else:
        st.warning("Invalid Employee ID")

# -----------------------------
# DUPLICATE CHECK
# -----------------------------
response_sheet = ss.worksheet("Responses")
existing_ids = [str(x).strip() for x in response_sheet.col_values(1)]

if emp_id and emp_id in existing_ids:
    st.error("Already submitted")
    st.stop()

# -----------------------------
# LEGEND
# -----------------------------
st.markdown("""
<div style='text-align:center; font-size:18px; font-weight:700; margin:10px;'>
🟢 Low Preferred Course &nbsp;&nbsp;&nbsp; 🔴 High Preferred Course
</div>
""", unsafe_allow_html=True)

# -----------------------------
# COURSE LIST
# -----------------------------
b1_courses = b1_df["Course"].dropna().tolist()
b2_courses = b2_df["Course"].dropna().tolist()

col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1
# -----------------------------
with col1:
    st.markdown("<div class='basket1'>📘 Basket 1</div>", unsafe_allow_html=True)
    b1_selected = st.multiselect("Select exactly 7 courses", b1_courses)
    st.write(f"Selected: {len(b1_selected)} / 7")

    for c in b1_selected[:7]:
        row = b1_df[b1_df["Course"] == c].iloc[0]
        if row["Usage"] < row["Max"]:
            st.markdown(f"<div class='green'>🟢 {c}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='red'>🔴 {c}</div>", unsafe_allow_html=True)

# -----------------------------
# BASKET 2
# -----------------------------
with col2:
    st.markdown("<div class='basket2'>📗 Basket 2</div>", unsafe_allow_html=True)
    b2_selected = st.multiselect("Select exactly 7 courses", b2_courses)
    st.write(f"Selected: {len(b2_selected)} / 7")

    for c in b2_selected[:7]:
        row = b2_df[b2_df["Course"] == c].iloc[0]
        if row["Usage"] < row["Max"]:
            st.markdown(f"<div class='green'>🟢 {c}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='red'>🔴 {c}</div>", unsafe_allow_html=True)

# -----------------------------
# UPDATE USAGE
# -----------------------------
def update_usage(sheet_name, selected, df):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()

    headers = data[0]
    rows = data[1:]

    c_idx = headers.index("Course")
    u_idx = headers.index("Usage")

    usage = {r[c_idx]: int(r[u_idx]) if r[u_idx] else 0 for r in rows}
    max_map = dict(zip(df["Course"], df["Max"]))

    for c in selected[:7]:
        if usage[c] < max_map[c]:
            usage[c] += 1

    updated = [[usage[r[c_idx]]] for r in rows]
    col_letter = chr(65 + u_idx)
    sheet.update(f"{col_letter}2:{col_letter}{len(rows)+1}", updated)

# -----------------------------
# SUBMIT
# -----------------------------
if st.button("🚀 Submit Preferences"):

    if st.session_state.name is None:
        st.error("Enter valid Employee ID")
        st.stop()

    if len(b1_selected) != 7 or len(b2_selected) != 7:
        st.error("Select exactly 7 courses in each basket")
        st.stop()

    try:
        update_usage("Basket1", b1_selected, b1_df)
        update_usage("Basket2", b2_selected, b2_df)

        response_sheet.append_row([
            emp_id,
            st.session_state.name,
            st.session_state.designation,
            *b1_selected[:7],
            *b2_selected[:7]
        ])

        st.session_state.submitted = True
        st.rerun()

    except Exception as e:
        st.error(str(e))
