#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
'''import io
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
# LOAD COURSE BASKETS
# -----------------------------
@st.cache_data(ttl=60)
def load_courses(sheet_name):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()
    if not data or len(data) < 2:
        return []
    
    # Extract row items from the first column starting after headers
    courses = [str(row[0]).strip() for row in data[1:] if row and str(row[0]).strip()]
    return courses

b1_courses = load_courses("Basket1")
b2_courses = load_courses("Basket2")

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
    
    emp_col = next((c for c in df.columns if "emp" in str(c).strip().lower() or "id" in str(c).strip().lower()), df.columns[0])
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
            name_col = next((c for c in row.columns if "name" in str(c).strip().lower()), row.columns[1])
            desig_col = next((c for c in row.columns if "desig" in str(c).strip().lower()), row.columns[2])
            
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
# SESSION STATE & HANDLERS
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

col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1 SELECTION
# -----------------------------
with col1:
    st.markdown("<div class='basket1'>📘 Basket 1</div>", unsafe_allow_html=True)
    st.multiselect("Select exactly 7 courses", b1_courses, key="b1", on_change=handle_b1_change)
    st.write(f"Selected: {len(st.session_state.b1)} / 7")

    for c in st.session_state.b1:
        st.markdown(f"• {c}")

# -----------------------------
# BASKET 2 SELECTION
# -----------------------------
with col2:
    st.markdown("<div class='basket2'>📗 Basket 2</div>", unsafe_allow_html=True)
    st.multiselect("Select exactly 7 courses", b2_courses, key="b2", on_change=handle_b2_change)
    st.write(f"Selected: {len(st.session_state.b2)} / 7")

    for c in st.session_state.b2:
        st.markdown(f"• {c}")

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

        with col_status:
            st.success("🎉 Submitted Successfully")

    except Exception as e:
        st.error(f"Error submitting: {e}")

# Render download button if PDF generation succeeded
if st.session_state.pdf_buffer:
    with col_download:
        st.download_button(
            "📄 Download PDF Report",
            data=st.session_state.pdf_buffer,
            file_name=f"{emp_id}_preferences.pdf",
            mime="application/pdf",
        )'''
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
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
# LOAD COURSE BASKETS
# -----------------------------
@st.cache_data(ttl=60)
def load_courses(sheet_name):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()
    if not data or len(data) < 2:
        return []
    
    courses = [str(row[0]).strip() for row in data[1:] if row and str(row[0]).strip()]
    return courses

b1_courses = load_courses("Basket1")
b2_courses = load_courses("Basket2")

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
    
    emp_col = next((c for c in df.columns if "emp" in str(c).strip().lower() or "id" in str(c).strip().lower()), df.columns[0])
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
            name_col = next((c for c in row.columns if "name" in str(c).strip().lower()), row.columns[1])
            desig_col = next((c for c in row.columns if "desig" in str(c).strip().lower()), row.columns[2])
            
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
# SESSION STATE & HANDLERS
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

col1, col2 = st.columns(2)

# -----------------------------
# BASKET 1 SELECTION
# -----------------------------
with col1:
    st.markdown("<div class='basket1'>📘 Basket 1</div>", unsafe_allow_html=True)
    st.multiselect("Select exactly 7 courses", b1_courses, key="b1", on_change=handle_b1_change)
    st.write(f"Selected: {len(st.session_state.b1)} / 7")

# -----------------------------
# BASKET 2 SELECTION
# -----------------------------
with col2:
    st.markdown("<div class='basket2'>📗 Basket 2</div>", unsafe_allow_html=True)
    st.multiselect("Select exactly 7 courses", b2_courses, key="b2", on_change=handle_b2_change)
    st.write(f"Selected: {len(st.session_state.b2)} / 7")

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

        with col_status:
            st.success("🎉 Submitted Successfully")

    except Exception as e:
        st.error(f"Error submitting: {e}")

# Render download button if PDF generation succeeded
if st.session_state.pdf_buffer:
    with col_download:
        st.download_button(
            "📄 Download PDF Report",
            data=st.session_state.pdf_buffer,
            file_name=f"{emp_id}_preferences.pdf",
            mime="application/pdf",
        )
