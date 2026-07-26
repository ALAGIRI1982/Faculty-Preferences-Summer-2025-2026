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
#-------------------------------------------------------------------------------------------------------------
import io
import pandas as pd
import streamlit as st
import gspread
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
# UI STYLING
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
    text-align: center;
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 20px;
}
.basket1 {
    background: linear-gradient(90deg, #2563eb, #3b82f6);
    padding: 10px 15px;
    border-radius: 10px;
    color: white;
    font-weight: bold;
}
.basket2 {
    background: linear-gradient(90deg, #ec4899, #f43f5e);
    padding: 10px 15px;
    border-radius: 10px;
    color: white;
    font-weight: bold;
}
.stButton>button {
    background: linear-gradient(90deg, #7c3aed, #ec4899);
    color: white;
    font-weight: bold;
    border-radius: 10px;
    height: 50px;
    width: 100%;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='title'>🎓 Faculty Course Preference System Fall 2026-2027</div>",
    unsafe_allow_html=True,
)

# -----------------------------
# GOOGLE SHEETS SETUP
# -----------------------------
SPREADSHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"

@st.cache_resource
def get_spreadsheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

ss = get_spreadsheet()

# -----------------------------
# LOAD DATA (SAFE FROM LIST.INDEX ERRORS)
# -----------------------------
@st.cache_data(ttl=60)
def load_basket_courses(sheet_name):
    try:
        sheet = ss.worksheet(sheet_name)
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return []
        
        # Pull the first column safely regardless of header name
        return [str(row[0]).strip() for row in data[1:] if row and str(row[0]).strip()]
    except Exception:
        return []

@st.cache_data(ttl=60)
def load_employees():
    try:
        sheet = ss.worksheet("Faculty List")
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return pd.DataFrame(columns=["EmpID", "Name", "Designation"])
        
        # Clean headers and values manually without relying on Pandas list index lookups
        headers = [str(h).strip().lower() for h in data[0]]
        
        emp_idx = next((i for i, h in enumerate(headers) if "emp" in h or "id" in h), 0)
        name_idx = next((i for i, h in enumerate(headers) if "name" in h), 1)
        desig_idx = next((i for i, h in enumerate(headers) if "desig" in h), 2)

        rows = []
        for r in data[1:]:
            if len(r) > emp_idx and str(r[emp_idx]).strip():
                rows.append({
                    "EmpID": str(r[emp_idx]).strip(),
                    "Name": str(r[name_idx]).strip() if len(r) > name_idx else "",
                    "Designation": str(r[desig_idx]).strip() if len(r) > desig_idx else ""
                })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["EmpID", "Name", "Designation"])

@st.cache_data(ttl=15)
def load_submitted_ids():
    try:
        sheet = ss.worksheet("Responses")
        col_vals = sheet.col_values(1)
        if not col_vals:
            return set()
        return set(str(v).strip() for v in col_vals[1:]) # Exclude header
    except Exception:
        return set()

b1_courses = load_basket_courses("Basket1")
b2_courses = load_basket_courses("Basket2")
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

    info = [["Employee ID", emp_id], ["Name", name], ["Designation", designation]]
    content.append(Table(info))
    content.append(Spacer(1, 15))

    b1_table = [["S.No", "Basket 1 Course"]] + [[i, c] for i, c in enumerate(b1, 1)]
    content.append(Paragraph("<b>Basket 1 Preferences</b>", styles["Heading2"]))
    content.append(Table(b1_table))
    content.append(Spacer(1, 15))

    b2_table = [["S.No", "Basket 2 Course"]] + [[i, c] for i, c in enumerate(b2, 1)]
    content.append(Paragraph("<b>Basket 2 Preferences</b>", styles["Heading2"]))
    content.append(Table(b2_table))

    doc.build(content)
    buffer.seek(0)
    return buffer

# -----------------------------
# UI FORM INPUT
# -----------------------------
col_emp, col_details = st.columns([1, 2])

with col_emp:
    emp_id = st.text_input("Enter Employee ID").strip()

name, designation = None, None

with col_details:
    if emp_id and "EmpID" in employees.columns and not employees.empty:
        row = employees[employees["EmpID"] == emp_id]
        if not row.empty:
            name = row.iloc[0].get("Name", "")
            designation = row.iloc[0].get("Designation", "")
            st.success("Employee Identified")
            st.markdown(f"**👤 Name:** {name} &nbsp;&nbsp;|&nbsp;&nbsp; **💼 Designation:** {designation}")
        else:
            st.error("Invalid Employee ID")

if emp_id and emp_id in load_submitted_ids():
    st.error("⚠️ Preferences for this Employee ID have already been submitted.")
    st.stop()

# -----------------------------
# SESSION STATE & CALLBACKS
# -----------------------------
if "b1" not in st.session_state:
    st.session_state.b1 = []
if "b2" not in st.session_state:
    st.session_state.b2 = []
if "submitted_pdf" not in st.session_state:
    st.session_state.submitted_pdf = None

def clamp_selection(key):
    if len(st.session_state[key]) > 7:
        st.session_state[key] = st.session_state[key][:7]

col1, col2 = st.columns(2)

# Basket 1 UI
with col1:
    st.markdown("<div class='basket1'>📘 Basket 1</div>", unsafe_allow_html=True)
    st.multiselect(
        "Select exactly 7 courses",
        options=b1_courses,
        key="b1",
        on_change=clamp_selection,
        args=("b1",),
    )
    st.write(f"Selected: **{len(st.session_state.b1)} / 7**")

# Basket 2 UI
with col2:
    st.markdown("<div class='basket2'>📗 Basket 2</div>", unsafe_allow_html=True)
    st.multiselect(
        "Select exactly 7 courses",
        options=b2_courses,
        key="b2",
        on_change=clamp_selection,
        args=("b2",),
    )
    st.write(f"Selected: **{len(st.session_state.b2)} / 7**")

# -----------------------------
# SUBMIT & DOWNLOAD
# -----------------------------
st.markdown("---")
col_submit, col_download = st.columns([1, 1])

with col_submit:
    submit_clicked = st.button("🚀 Submit Preferences")

if submit_clicked:
    if not name:
        st.error("Please enter a valid Employee ID before submitting.")
        st.stop()

    if len(st.session_state.b1) != 7 or len(st.session_state.b2) != 7:
        st.error("⚠️ You must select exactly 7 courses in both Basket 1 and Basket 2.")
        st.stop()

    try:
        with st.spinner("Submitting your preferences..."):
            response_sheet = ss.worksheet("Responses")
            
            # Construct row data
            new_row = [
                str(emp_id),
                str(name),
                str(designation),
                *[str(c) for c in st.session_state.b1],
                *[str(c) for c in st.session_state.b2]
            ]
            
            # Safe append without gspread table indexing
            response_sheet.append_row(new_row, value_input_option="USER_ENTERED")

            # Generate PDF and write to session state
            st.session_state.submitted_pdf = generate_pdf(
                emp_id, name, designation,
                st.session_state.b1,
                st.session_state.b2
            )
            
            # Clear cache so the submission is immediately recognized
            st.cache_data.clear()

        st.success("🎉 Preferences submitted successfully!")

    except Exception as e:
        import traceback
        st.error(f"Error recording preferences: {e}")
        st.code(traceback.format_exc())

# Render download button independently using session state PDF
if st.session_state.submitted_pdf:
    with col_download:
        st.download_button(
            label="📄 Download Preference PDF",
            data=st.session_state.submitted_pdf,
            file_name=f"{emp_id}_preferences.pdf",
            mime="application/pdf"
        )
