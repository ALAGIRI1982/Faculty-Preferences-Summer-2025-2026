'''import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# PDF IMPORTS
from reportlab.platypus import SimpleDocTemplate, Table, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import io

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

# -----------------------------
# TITLE
# -----------------------------
st.markdown("<div class='title'>🎓 Faculty Course Preference System Fall 2026-2027</div>", unsafe_allow_html=True)

# -----------------------------
# GOOGLE SHEETS AUTH
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
    df["Course"] = df["Course"].astype(str).str.strip()
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
# PDF GENERATION
# -----------------------------
def generate_pdf(emp_id, name, designation, b1, b2):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("<b>FACULTY PREFERENCE REPORT</b>", styles["Title"]))
    content.append(Spacer(1, 15))

    info = [
        ["Employee ID", emp_id],
        ["Name", name],
        ["Designation", designation]
    ]

    content.append(Table(info))
    content.append(Spacer(1, 15))

    b1_table = [["S.No", "Basket 1 Course"]]
    for i, c in enumerate(b1, 1):
        b1_table.append([i, c])

    content.append(Paragraph("<b>Basket 1</b>", styles["Heading2"]))
    content.append(Table(b1_table))
    content.append(Spacer(1, 15))

    b2_table = [["S.No", "Basket 2 Course"]]
    for i, c in enumerate(b2, 1):
        b2_table.append([i, c])

    content.append(Paragraph("<b>Basket 2</b>", styles["Heading2"]))
    content.append(Table(b2_table))

    doc.build(content)
    buffer.seek(0)
    return buffer

# -----------------------------
# EMP INPUT + DETAILS
# -----------------------------
col_emp, col_details = st.columns([1, 2])

with col_emp:
    emp_id = st.text_input("Enter Employee ID")

with col_details:
    name = None
    designation = None

    if emp_id:
        row = employees[employees["EmpID"] == emp_id.strip()]
        if not row.empty:
            name = row.iloc[0]["Name"]
            designation = row.iloc[0]["Designation"]

            st.success("Employee Found")
            st.markdown("### 👤 Employee Details")

            st.markdown(
                f"""
                <div style="display:flex; gap:40px; font-size:18px; font-weight:600;">
                    <div>👤 Name: {name}</div>
                    <div>💼 Designation: {designation}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
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
# SESSION STATE
# -----------------------------
if "b1" not in st.session_state:
    st.session_state.b1 = []

if "b2" not in st.session_state:
    st.session_state.b2 = []

def handle_b1_change():
    if len(st.session_state.b1) > 7:
        st.session_state.b1 = st.session_state.b1[:7]

def handle_b2_change():
    if len(st.session_state.b2) > 7:
        st.session_state.b2 = st.session_state.b2[:7]

b1_courses = b1_df["Course"].tolist()
b2_courses = b2_df["Course"].tolist()

col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1
# -----------------------------
with col1:
    st.markdown("<div class='basket1'>📘 Basket 1</div>", unsafe_allow_html=True)

    st.multiselect("Select exactly 7 courses", b1_courses, key="b1", on_change=handle_b1_change)
    st.write(f"Selected: {len(st.session_state.b1)} / 7")

    for c in st.session_state.b1:
        match = b1_df[b1_df["Course"].str.strip() == str(c).strip()]
        if not match.empty:
            row = match.iloc[0]
            color = "green" if row["Usage"] < row["Max"] else "red"
            icon = "🟢" if color == "green" else "🔴"
            st.markdown(f"<div class='{color}'>{icon} {c}</div>", unsafe_allow_html=True)

# -----------------------------
# BASKET 2
# -----------------------------
with col2:
    st.markdown("<div class='basket2'>📗 Basket 2</div>", unsafe_allow_html=True)

    st.multiselect("Select exactly 7 courses", b2_courses, key="b2", on_change=handle_b2_change)
    st.write(f"Selected: {len(st.session_state.b2)} / 7")

    for c in st.session_state.b2:
        match = b2_df[b2_df["Course"].str.strip() == str(c).strip()]
        if not match.empty:
            row = match.iloc[0]
            color = "green" if row["Usage"] < row["Max"] else "red"
            icon = "🟢" if color == "green" else "🔴"
            st.markdown(f"<div class='{color}'>{icon} {c}</div>", unsafe_allow_html=True)

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

    for c in selected:
        if usage[c] < max_map[c]:
            usage[c] += 1

    updated = [[usage[r[c_idx]]] for r in rows]
    col_letter = chr(65 + u_idx)
    sheet.update(f"{col_letter}2:{col_letter}{len(rows)+1}", updated)

# -----------------------------
# SUBMIT (RIGHT SIDE UI FIXED)
# -----------------------------
col_submit, col_download, col_status = st.columns([1, 1, 1])

with col_submit:
    submit_clicked = st.button("🚀 Submit Preferences")

if submit_clicked:

    if name is None:
        st.error("Enter valid Employee ID")
        st.stop()

    if len(st.session_state.b1) != 7 or len(st.session_state.b2) != 7:
        st.error("⚠️ Select exactly 7 courses in each basket")
        st.stop()

    try:
        update_usage("Basket1", st.session_state.b1, b1_df)
        update_usage("Basket2", st.session_state.b2, b2_df)

        response_sheet.append_row([
            emp_id, name, designation,
            *st.session_state.b1,
            *st.session_state.b2
        ])

        pdf_file = generate_pdf(
            emp_id, name, designation,
            st.session_state.b1,
            st.session_state.b2
        )

        with col_download:
            st.download_button(
                "📄 Download PDF Report",
                data=pdf_file,
                file_name=f"{emp_id}_preferences.pdf",
                mime="application/pdf"
            )

        with col_status:
            st.success("🎉 Submitted Successfully")

    except Exception as e:
        st.error(str(e))'''
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
import io
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# PDF IMPORTS
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Faculty Preference System", layout="wide")

# -----------------------------
# 🌈 UI STYLING
# -----------------------------
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# -----------------------------
# TITLE
# -----------------------------
st.markdown(
    "<div class='title'>🎓 Faculty Course Preference System Fall 2026-2027</div>",
    unsafe_allow_html=True,
)

# -----------------------------
# GOOGLE SHEETS AUTH
# -----------------------------
SPREADSHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"

@st.cache_resource
def get_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
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
    if not data or len(data) < 2:
        return pd.DataFrame(columns=["Course", "Usage", "Max"])
    
    headers = [str(h).strip() for h in data[0]]
    return pd.DataFrame(data[1:], columns=headers)

def clean_df(df):
    # Flexible column matching
    course_col = next((c for c in df.columns if "course" in str(c).strip().lower()), "Course")
    usage_col = next((c for c in df.columns if "usage" in str(c).strip().lower()), "Usage")
    max_col = next((c for c in df.columns if "max" in str(c).strip().lower()), "Max")

    df["Usage"] = pd.to_numeric(df.get(usage_col, 0), errors="coerce").fillna(0).astype(int)
    df["Max"] = pd.to_numeric(df.get(max_col, 0), errors="coerce").fillna(0).astype(int)
    df["Course"] = df.get(course_col, "").astype(str).str.strip()
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
    if not data or len(data) < 2:
        return pd.DataFrame(columns=["EmpID", "Name", "Designation"])
    
    headers = [str(h).strip() for h in data[0]]
    df = pd.DataFrame(data[1:], columns=headers)
    
    emp_col = next((c for c in df.columns if "emp" in str(c).strip().lower() or "id" in str(c).strip().lower()), "EmpID")
    df["EmpID"] = df[emp_col].astype(str).str.strip()
    return df

employees = load_employees()

# -----------------------------
# PDF GENERATION
# -----------------------------
def generate_pdf(emp_id, name, designation, b1, b2):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("<b>FACULTY PREFERENCE REPORT</b>", styles["Title"]))
    content.append(Spacer(1, 15))

    info = [
        ["Employee ID", emp_id],
        ["Name", name],
        ["Designation", designation],
    ]

    content.append(Table(info))
    content.append(Spacer(1, 15))

    b1_table = [["S.No", "Basket 1 Course"]]
    for i, c in enumerate(b1, 1):
        b1_table.append([i, c])

    content.append(Paragraph("<b>Basket 1</b>", styles["Heading2"]))
    content.append(Table(b1_table))
    content.append(Spacer(1, 15))

    b2_table = [["S.No", "Basket 2 Course"]]
    for i, c in enumerate(b2, 1):
        b2_table.append([i, c])

    content.append(Paragraph("<b>Basket 2</b>", styles["Heading2"]))
    content.append(Table(b2_table))

    doc.build(content)
    buffer.seek(0)
    return buffer

# -----------------------------
# EMP INPUT + DETAILS
# -----------------------------
col_emp, col_details = st.columns([1, 2])

with col_emp:
    emp_id = st.text_input("Enter Employee ID")

with col_details:
    name = None
    designation = None

    if emp_id:
        row = employees[employees["EmpID"] == emp_id.strip()]
        if not row.empty:
            name_col = next((c for c in row.columns if "name" in str(c).strip().lower()), "Name")
            desig_col = next((c for c in row.columns if "desig" in str(c).strip().lower()), "Designation")
            
            name = row.iloc[0].get(name_col, "")
            designation = row.iloc[0].get(desig_col, "")

            st.success("Employee Found")
            st.markdown("### 👤 Employee Details")

            st.markdown(
                f"""
                <div style="display:flex; gap:40px; font-size:18px; font-weight:600;">
                    <div>👤 Name: {name}</div>
                    <div>💼 Designation: {designation}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("Invalid Employee ID")

# -----------------------------
# DUPLICATE CHECK
# -----------------------------
response_sheet = ss.worksheet("Responses")
existing_ids = [str(x).strip() for x in response_sheet.col_values(1)]

if emp_id and emp_id.strip() in existing_ids:
    st.error("Already submitted")
    st.stop()

# -----------------------------
# SESSION STATE
# -----------------------------
if "b1" not in st.session_state:
    st.session_state.b1 = []

if "b2" not in st.session_state:
    st.session_state.b2 = []

if "pdf_buffer" not in st.session_state:
    st.session_state.pdf_buffer = None

def handle_b1_change():
    if len(st.session_state.b1) > 7:
        st.session_state.b1 = st.session_state.b1[:7]

def handle_b2_change():
    if len(st.session_state.b2) > 7:
        st.session_state.b2 = st.session_state.b2[:7]

b1_courses = b1_df["Course"].tolist()
b2_courses = b2_df["Course"].tolist()

col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1
# -----------------------------
with col1:
    st.markdown("<div class='basket1'>📘 Basket 1</div>", unsafe_allow_html=True)

    st.multiselect("Select exactly 7 courses", b1_courses, key="b1", on_change=handle_b1_change)
    st.write(f"Selected: {len(st.session_state.b1)} / 7")

    for c in st.session_state.b1:
        match = b1_df[b1_df["Course"].str.strip() == str(c).strip()]
        if not match.empty:
            row = match.iloc[0]
            color = "green" if row["Usage"] < row["Max"] else "red"
            icon = "🟢" if color == "green" else "🔴"
            st.markdown(f"<div class='{color}'>{icon} {c}</div>", unsafe_allow_html=True)

# -----------------------------
# BASKET 2
# -----------------------------
with col2:
    st.markdown("<div class='basket2'>📗 Basket 2</div>", unsafe_allow_html=True)

    st.multiselect("Select exactly 7 courses", b2_courses, key="b2", on_change=handle_b2_change)
    st.write(f"Selected: {len(st.session_state.b2)} / 7")

    for c in st.session_state.b2:
        match = b2_df[b2_df["Course"].str.strip() == str(c).strip()]
        if not match.empty:
            row = match.iloc[0]
            color = "green" if row["Usage"] < row["Max"] else "red"
            icon = "🟢" if color == "green" else "🔴"
            st.markdown(f"<div class='{color}'>{icon} {c}</div>", unsafe_allow_html=True)

# -----------------------------
# UPDATE USAGE (SAFE LOOKUP)
# -----------------------------
def update_usage(sheet_name, selected, df):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()
    if not data or len(data) < 2:
        return

    # Clean headers to safely find column positions
    clean_headers = [str(h).strip().lower() for h in data[0]]

    # Safe index lookup matching substrings
    c_idx = next((i for i, h in enumerate(clean_headers) if "course" in h), None)
    u_idx = next((i for i, h in enumerate(clean_headers) if "usage" in h or "count" in h), None)

    if c_idx is None or u_idx is None:
        raise ValueError(
            f"Worksheet '{sheet_name}' must have headers for 'Course' and 'Usage'. Found: {data[0]}"
        )

    rows = data[1:]
    usage = {r[c_idx].strip(): int(r[u_idx]) if len(r) > u_idx and r[u_idx].isdigit() else 0 for r in rows}
    max_map = dict(zip(df["Course"], df["Max"]))

    for c in selected:
        c_str = str(c).strip()
        if c_str in usage and c_str in max_map:
            if usage[c_str] < max_map[c_str]:
                usage[c_str] += 1

    updated = [[usage.get(r[c_idx].strip(), 0)] for r in rows]
    col_letter = chr(65 + u_idx)
    sheet.update(f"{col_letter}2:{col_letter}{len(rows)+1}", updated)

# -----------------------------
# SUBMIT & DOWNLOAD
# -----------------------------
col_submit, col_download, col_status = st.columns([1, 1, 1])

with col_submit:
    submit_clicked = st.button("🚀 Submit Preferences")

if submit_clicked:
    if name is None:
        st.error("Enter valid Employee ID")
        st.stop()

    if len(st.session_state.b1) != 7 or len(st.session_state.b2) != 7:
        st.error("⚠️ Select exactly 7 courses in each basket")
        st.stop()

    try:
        with st.spinner("Submitting..."):
            update_usage("Basket1", st.session_state.b1, b1_df)
            update_usage("Basket2", st.session_state.b2, b2_df)

            response_sheet.append_row([
                emp_id, name, designation,
                *st.session_state.b1,
                *st.session_state.b2
            ])

            st.session_state.pdf_buffer = generate_pdf(
                emp_id, name, designation,
                st.session_state.b1,
                st.session_state.b2
            )

            st.cache_data.clear()

        with col_status:
            st.success("🎉 Submitted Successfully")

    except Exception as e:
        st.error(f"Error submitting: {e}")

# Render download button if PDF is ready
if st.session_state.pdf_buffer:
    with col_download:
        st.download_button(
            "📄 Download PDF Report",
            data=st.session_state.pdf_buffer,
            file_name=f"{emp_id}_preferences.pdf",
            mime="application/pdf",
        )

