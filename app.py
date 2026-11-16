'''import io
from datetime import datetime
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# PDF IMPORTS
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
    background: rgba(255, 255, 255, 0.96);
    padding: 30px;
    border-radius: 18px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
}
.title {
    text-align: center;
    font-size: 36px;
    font-weight: 800;
    color: #1e293b;
    margin-bottom: 20px;
}
.basket1 {
    background: linear-gradient(90deg, #2563eb, #3b82f6);
    padding: 12px 16px;
    border-radius: 10px;
    color: white;
    font-weight: bold;
    font-size: 18px;
    margin-bottom: 12px;
}
.basket2 {
    background: linear-gradient(90deg, #ec4899, #f43f5e);
    padding: 12px 16px;
    border-radius: 10px;
    color: white;
    font-weight: bold;
    font-size: 18px;
    margin-bottom: 12px;
}
.summary-header {
    background: linear-gradient(90deg, #0f172a, #334155);
    padding: 12px 16px;
    border-radius: 10px;
    color: white;
    font-weight: bold;
    font-size: 18px;
    margin-bottom: 12px;
}
.course-pill {
    background-color: #f1f5f9;
    border-left: 4px solid #3b82f6;
    padding: 7px 12px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    color: #0f172a;
}
.course-pill-b2 {
    background-color: #fdf2f8;
    border-left: 4px solid #ec4899;
    padding: 7px 12px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    color: #0f172a;
}
span[data-baseweb="tag"] {
    margin: 3px !important;
    padding: 4px 10px !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(90deg, #7c3aed, #ec4899);
    color: white;
    font-weight: bold;
    border-radius: 10px;
    height: 50px;
    width: 100%;
    border: none;
    font-size: 16px;
}
.stDownloadButton>button {
    background: linear-gradient(90deg, #059669, #10b981);
    color: white;
    font-weight: bold;
    border-radius: 10px;
    height: 50px;
    width: 100%;
    border: none;
    font-size: 16px;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# TITLE
# -----------------------------
st.markdown(
    "<div class='title'>🎓 Faculty Course Preference System Winter 2026-2027</div>",
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
# LOAD COURSE BASKETS (LONG CACHE TTL TO SAVE API QUOTA)
# -----------------------------
@st.cache_data(ttl=300)
def load_courses(sheet_name):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()
    if not data or len(data) < 2:
        return []
    return [str(row[0]).strip() for row in data[1:] if row and str(row[0]).strip()]

b1_courses = load_courses("Basket1")
b2_courses = load_courses("Basket2")

# -----------------------------
# EMPLOYEE DATA
# -----------------------------
@st.cache_data(ttl=300)
def load_employees():
    sheet = ss.worksheet("Faculty List")
    data = sheet.get_all_values()
    if not data or len(data) < 2:
        return pd.DataFrame(columns=["EmpID", "Name", "Designation"])

    headers = [str(h).strip() for h in data[0]]
    df = pd.DataFrame(data[1:], columns=headers)

    emp_col = next(
        (c for c in df.columns if "emp" in str(c).strip().lower() or "id" in str(c).strip().lower()),
        df.columns[0],
    )
    df["EmpID"] = df[emp_col].astype(str).str.strip()
    return df

employees = load_employees()

# -----------------------------
# STYLED PDF GENERATION
# -----------------------------
def generate_pdf(emp_id, name, designation, b1, b2, timestamp):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("<b>FACULTY COURSE PREFERENCE REPORT (WINTER 2026-2027)</b>", styles["Title"]))
    content.append(Spacer(1, 15))

    info = [
        ["Employee ID", emp_id],
        ["Name", name],
        ["Designation", designation],
        ["Submitted At", timestamp],
    ]
    info_table = Table(info, colWidths=[130, 340])
    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    content.append(info_table)
    content.append(Spacer(1, 18))

    def build_basket_table(title, courses, header_color):
        content.append(Paragraph(f"<b>{title}</b>", styles["Heading2"]))
        table_data = [["Preference", "Course Name"]]
        for i, c in enumerate(courses, 1):
            table_data.append([f"#{i}", Paragraph(c, styles["Normal"])])

        t = Table(table_data, colWidths=[80, 390])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        content.append(t)
        content.append(Spacer(1, 15))

    build_basket_table("Basket 1 Preferences", b1, colors.HexColor("#2563eb"))
    build_basket_table("Basket 2 Preferences", b2, colors.HexColor("#ec4899"))

    doc.build(content)
    buffer.seek(0)
    return buffer

# -----------------------------
# SESSION STATE INIT
# -----------------------------
for key, default in [
    ("b1", []),
    ("b2", []),
    ("pdf_buffer", None),
    ("submitted_emp", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def handle_b1_change():
    if len(st.session_state.b1) > 7:
        st.session_state.b1 = st.session_state.b1[:7]

def handle_b2_change():
    if len(st.session_state.b2) > 7:
        st.session_state.b2 = st.session_state.b2[:7]

def move_item(basket_key, index, direction):
    items = list(st.session_state[basket_key])
    new_idx = index + direction
    if 0 <= new_idx < len(items):
        items[index], items[new_idx] = items[new_idx], items[index]
        st.session_state[basket_key] = items

# -----------------------------
# STEP 1: EMP INPUT + DETAILS
# -----------------------------
with st.container(border=True):
    col_emp, col_details = st.columns([1, 2], gap="large")

    with col_emp:
        emp_id = st.text_input("Enter Employee ID", placeholder="Type your Employee ID...").strip()

    with col_details:
        name = None
        designation = None

        if emp_id:
            row = employees[employees["EmpID"] == emp_id]
            if not row.empty:
                name_col = next((c for c in row.columns if "name" in str(c).strip().lower()), row.columns[1])
                desig_col = next((c for c in row.columns if "desig" in str(c).strip().lower()), row.columns[2])

                name = row.iloc[0].get(name_col, "")
                designation = row.iloc[0].get(desig_col, "")

                st.success("✅ Employee Verified")
                st.markdown(
                    f"""
                    <div style="display:flex; flex-wrap:wrap; gap:30px; font-size:17px; font-weight:600; padding-top:4px;">
                        <div>👤 <b>Name:</b> {name}</div>
                        <div>💼 <b>Designation:</b> {designation}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.warning("⚠️ Invalid Employee ID")

# -----------------------------
# DUPLICATE CHECK (PRESERVES PDF DOWNLOAD JUST AFTER SUBMIT)
# -----------------------------
@st.cache_data(ttl=15)
def get_submitted_ids():
    try:
        response_sheet = ss.worksheet("Responses")
        return [str(x).strip() for x in response_sheet.col_values(1) if x]
    except Exception:
        return []

is_just_submitted = (emp_id and st.session_state.submitted_emp == emp_id)

if emp_id and not is_just_submitted:
    if emp_id in get_submitted_ids():
        st.error("🚫 Preferences have already been submitted for this Employee ID.")
        st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# STEP 2: SPLIT-VIEW COURSE SELECTION + REORDERABLE SUMMARY
# -----------------------------
form_disabled = (name is None) or is_just_submitted
left_col, right_col = st.columns([1.45, 1], gap="large")

with left_col:
    with st.container(border=True):
        st.markdown("<div class='basket1'>📘 Basket 1 — Select 7 Courses</div>", unsafe_allow_html=True)
        st.multiselect(
            "Search and pick 7 courses (1st choice first):",
            b1_courses,
            key="b1",
            on_change=handle_b1_change,
            disabled=form_disabled,
            placeholder="Enter Employee ID above to unlock..." if name is None else "Click to choose Basket 1 courses...",
        )
        st.progress(len(st.session_state.b1) / 7, text=f"Basket 1 Progress: {len(st.session_state.b1)} / 7 selected")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("<div class='basket2'>📗 Basket 2 — Select 7 Courses</div>", unsafe_allow_html=True)
        st.multiselect(
            "Search and pick 7 courses (1st choice first):",
            b2_courses,
            key="b2",
            on_change=handle_b2_change,
            disabled=form_disabled,
            placeholder="Enter Employee ID above to unlock..." if name is None else "Click to choose Basket 2 courses...",
        )
        st.progress(len(st.session_state.b2) / 7, text=f"Basket 2 Progress: {len(st.session_state.b2)} / 7 selected")

with right_col:
    with st.container(border=True):
        st.markdown("<div class='summary-header'>📋 Live Preference Summary (Use ↑/↓ to Rank)</div>", unsafe_allow_html=True)

        # Basket 1 Reorderable List
        st.markdown(f"**📘 Basket 1 ({len(st.session_state.b1)} / 7)**")
        if st.session_state.b1:
            for idx, course in enumerate(st.session_state.b1):
                c_text, c_up, c_down = st.columns([6, 1, 1], gap="small")
                with c_text:
                    st.markdown(f"<div class='course-pill'><b>#{idx+1}</b> &nbsp; {course}</div>", unsafe_allow_html=True)
                with c_up:
                    st.button("↑", key=f"b1_up_{idx}", disabled=(idx == 0 or form_disabled), on_click=move_item, args=("b1", idx, -1))
                with c_down:
                    st.button("↓", key=f"b1_dn_{idx}", disabled=(idx == len(st.session_state.b1) - 1 or form_disabled), on_click=move_item, args=("b1", idx, 1))
        else:
            st.caption("No courses selected from Basket 1 yet.")

        st.divider()

        # Basket 2 Reorderable List
        st.markdown(f"**📗 Basket 2 ({len(st.session_state.b2)} / 7)**")
        if st.session_state.b2:
            for idx, course in enumerate(st.session_state.b2):
                c_text, c_up, c_down = st.columns([6, 1, 1], gap="small")
                with c_text:
                    st.markdown(f"<div class='course-pill-b2'><b>#{idx+1}</b> &nbsp; {course}</div>", unsafe_allow_html=True)
                with c_up:
                    st.button("↑", key=f"b2_up_{idx}", disabled=(idx == 0 or form_disabled), on_click=move_item, args=("b2", idx, -1))
                with c_down:
                    st.button("↓", key=f"b2_dn_{idx}", disabled=(idx == len(st.session_state.b2) - 1 or form_disabled), on_click=move_item, args=("b2", idx, 1))
        else:
            st.caption("No courses selected from Basket 2 yet.")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# STEP 3: SUBMIT & DOWNLOAD
# -----------------------------
with st.container(border=True):
    col_submit, col_download, col_status = st.columns([1, 1, 1], gap="medium")

    with col_submit:
        submit_clicked = st.button("🚀 Submit Preferences", type="primary", disabled=form_disabled)

    if submit_clicked:
        if len(st.session_state.b1) != 7 or len(st.session_state.b2) != 7:
            with col_status:
                st.error("⚠️ Select exactly 7 courses in both baskets.")
            st.stop()

        try:
            with st.spinner("Submitting preferences..."):
                response_sheet = ss.worksheet("Responses")

                # Real-time duplicate check right before writing
                live_ids = [str(x).strip() for x in response_sheet.col_values(1) if x]
                if emp_id in live_ids:
                    with col_status:
                        st.error("🚫 Already submitted!")
                    st.stop()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                response_sheet.append_row([
                    emp_id,
                    name,
                    designation,
                    *st.session_state.b1,
                    *st.session_state.b2,
                    timestamp,
                ])

                st.session_state.pdf_buffer = generate_pdf(
                    emp_id,
                    name,
                    designation,
                    st.session_state.b1,
                    st.session_state.b2,
                    timestamp,
                )
                st.session_state.submitted_emp = emp_id
                get_submitted_ids.clear()
                st.rerun()

        except Exception as e:
            with col_status:
                st.error(f"Error submitting: {e}")

    if is_just_submitted and st.session_state.pdf_buffer:
        with col_status:
            st.success("🎉 Submitted Successfully!")
        with col_download:
            st.download_button(
                "📄 Download PDF Report",
                data=st.session_state.pdf_buffer,
                file_name=f"{emp_id}_preferences.pdf",
                mime="application/pdf",
            )'''
"""
Faculty Course Preference System – Winter 2026–2027
--------------------------------------------------
Streamlit + Google Sheets + PDF + Excel export.

Required Google Sheets worksheets:
  1. Basket1       First column contains course names (header in row 1)
  2. Basket2       First column contains course names (header in row 1)
  3. Faculty List  Must contain EmpID, Name, Designation columns
  4. Responses     Created automatically if it does not exist

Required Streamlit secrets (.streamlit/secrets.toml):
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
client_email = "..."
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
# Include the remaining fields from your service-account JSON if supplied.

[admin]
password = "CHANGE_THIS_TO_A_STRONG_ADMIN_PASSWORD"

Install:
pip install streamlit gspread pandas openpyxl google-auth reportlab
"""

from __future__ import annotations

import html
import io
import re
import time
import uuid
from datetime import datetime
from typing import Any

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="Faculty Course Preference System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

SPREADSHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"
SYSTEM_TITLE = "Faculty Course Preference System"
SEMESTER_TITLE = "Winter 2026–2027"
MAX_PREFERENCES = 7

RESPONSE_HEADERS = [
    "EmpID",
    "Name",
    "Designation",
    *[f"Basket1_P{i}" for i in range(1, 8)],
    *[f"Basket2_P{i}" for i in range(1, 8)],
    "SubmittedAt",
    "SubmissionRef",
]

# ---------------------------------------------------------------------
# MODERN UI
# ---------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 48%, #ecfeff 100%);
    }
    [data-testid="stHeader"] { background: rgba(255,255,255,0.72); }
    .block-container {
        max-width: 1440px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }
    .hero {
        background: linear-gradient(115deg, #0f172a 0%, #1e40af 55%, #0891b2 100%);
        padding: 28px 32px;
        border-radius: 20px;
        color: white;
        margin-bottom: 22px;
        box-shadow: 0 12px 30px rgba(15,23,42,.16);
    }
    .hero h1 {
        font-size: clamp(25px, 3vw, 36px);
        font-weight: 800;
        margin: 0 0 7px 0;
        color: white;
        letter-spacing: -0.7px;
    }
    .hero p {
        margin: 0;
        color: #dbeafe;
        font-size: 14px;
    }
    .section-card {
        background: rgba(255,255,255,.92);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 4px 16px rgba(15,23,42,.045);
    }
    .basket-title {
        padding: 12px 15px;
        border-radius: 11px;
        color: white;
        font-weight: 700;
        font-size: 16px;
        margin-bottom: 12px;
    }
    .basket-one { background: linear-gradient(90deg,#1d4ed8,#3b82f6); }
    .basket-two { background: linear-gradient(90deg,#be185d,#ec4899); }
    .summary-title {
        font-weight: 800;
        color: #0f172a;
        font-size: 17px;
        margin-bottom: 12px;
    }
    .preference-row {
        display: flex;
        align-items: center;
        gap: 10px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #3b82f6;
        border-radius: 9px;
        padding: 9px 11px;
        margin: 6px 0;
        color: #0f172a;
        font-size: 13px;
        overflow-wrap: anywhere;
    }
    .preference-row.pink { border-left-color: #ec4899; }
    .rank {
        background: #e2e8f0;
        color: #334155;
        border-radius: 7px;
        min-width: 28px;
        text-align: center;
        padding: 3px 5px;
        font-weight: 800;
    }
    .first-choice {
        background: #fef3c7;
        color: #92400e;
        border-radius: 6px;
        font-size: 10px;
        font-weight: 800;
        padding: 3px 6px;
        margin-left: auto;
        white-space: nowrap;
    }
    .small-note { color: #64748b; font-size: 12px; }
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(90deg,#1d4ed8,#0891b2);
        border: 0;
        color: white;
        border-radius: 10px;
        min-height: 46px;
        font-weight: 700;
    }
    div[data-testid="stDownloadButton"] > button {
        border-radius: 10px;
        min-height: 46px;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2e8f0;
        padding: 13px 15px;
        border-radius: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="hero">
        <h1>🎓 {html.escape(SYSTEM_TITLE)}</h1>
        <p>{html.escape(SEMESTER_TITLE)} &nbsp;|&nbsp; Faculty preference submission portal</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------------------------------------------------

@st.cache_resource
def get_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scopes,
    )
    return gspread.authorize(credentials)


@st.cache_resource
def get_spreadsheet():
    return get_client().open_by_key(SPREADSHEET_ID)


def get_worksheet(name: str, create: bool = False):
    spreadsheet = get_spreadsheet()
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        if create:
            return spreadsheet.add_worksheet(title=name, rows=1000, cols=25)
        raise


# ---------------------------------------------------------------------
# DATA LOADING AND NORMALIZATION
# ---------------------------------------------------------------------

def normalize_emp_id(value: Any) -> str:
    """Normalize IDs such as 10889.0 to 10889 without changing text IDs."""
    value = str(value or "").strip()
    if re.fullmatch(r"\d+\.0", value):
        return value[:-2]
    return value


@st.cache_data(ttl=300, show_spinner=False)
def load_courses(sheet_name: str) -> list[str]:
    values = get_worksheet(sheet_name).get_all_values()
    if len(values) < 2:
        return []
    courses = []
    seen = set()
    for row in values[1:]:
        if not row:
            continue
        course = str(row[0]).strip()
        if course and course.casefold() not in seen:
            courses.append(course)
            seen.add(course.casefold())
    return courses


@st.cache_data(ttl=300, show_spinner=False)
def load_employees() -> pd.DataFrame:
    values = get_worksheet("Faculty List").get_all_values()
    if not values:
        return pd.DataFrame(columns=["EmpID", "Name", "Designation"])

    headers = [str(x).strip() for x in values[0]]
    if not headers:
        return pd.DataFrame(columns=["EmpID", "Name", "Designation"])

    width = len(headers)
    rows = [(row + [""] * max(0, width - len(row)))[:width] for row in values[1:]]
    frame = pd.DataFrame(rows, columns=headers)

    def find_column(candidates, fallback=None):
        lowered = {str(c).strip().casefold(): c for c in frame.columns}
        for candidate in candidates:
            if candidate in lowered:
                return lowered[candidate]
        for column in frame.columns:
            col = str(column).strip().casefold()
            if any(candidate in col for candidate in candidates):
                return column
        return fallback

    emp_col = find_column(["empid", "employee id", "emp id", "id"], frame.columns[0])
    name_col = find_column(["name", "employee name"], frame.columns[1] if len(frame.columns) > 1 else None)
    designation_col = find_column(
        ["designation", "design"],
        frame.columns[2] if len(frame.columns) > 2 else None,
    )

    if name_col is None or designation_col is None:
        raise ValueError(
            "Faculty List must contain EmpID, Name and Designation columns."
        )

    result = pd.DataFrame(
        {
            "EmpID": frame[emp_col].map(normalize_emp_id),
            "Name": frame[name_col].astype(str).str.strip(),
            "Designation": frame[designation_col].astype(str).str.strip(),
        }
    )
    result = result[result["EmpID"] != ""].drop_duplicates("EmpID", keep="first")
    return result.reset_index(drop=True)


def ensure_response_headers():
    sheet = get_worksheet("Responses", create=True)
    first_row = sheet.row_values(1)
    if not first_row:
        sheet.append_row(RESPONSE_HEADERS, value_input_option="USER_ENTERED")
    return sheet


def get_response_records(force_refresh: bool = False) -> pd.DataFrame:
    """Read response data. This function is deliberately not cached for submission checks."""
    sheet = ensure_response_headers()
    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=RESPONSE_HEADERS)
    frame = pd.DataFrame(records)
    if "EmpID" in frame.columns:
        frame["EmpID"] = frame["EmpID"].map(normalize_emp_id)
    return frame


def submitted_ids_live() -> set[str]:
    sheet = ensure_response_headers()
    ids = sheet.col_values(1)[1:]
    return {normalize_emp_id(x) for x in ids if normalize_emp_id(x)}


# ---------------------------------------------------------------------
# PDF REPORT
# ---------------------------------------------------------------------

def generate_pdf(emp_id, name, designation, basket1, basket2, timestamp, reference):
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=38,
        leftMargin=38,
        topMargin=42,
        bottomMargin=42,
        title=f"Faculty Preferences - {emp_id}",
        author="Faculty Course Preference System",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#12306b"),
        spaceAfter=8,
    )
    course_style = ParagraphStyle(
        "CourseCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        wordWrap="CJK",
    )
    content = [
        Paragraph("FACULTY COURSE PREFERENCE REPORT", title_style),
        Paragraph(f"<b>{html.escape(SEMESTER_TITLE)}</b>", styles["Heading3"]),
        Spacer(1, 12),
    ]

    info = [
        ["Employee ID", html.escape(str(emp_id))],
        ["Name", html.escape(str(name))],
        ["Designation", html.escape(str(designation))],
        ["Submitted At", html.escape(str(timestamp))],
        ["Submission Reference", html.escape(str(reference))],
    ]
    info_table = Table(info, colWidths=[135, 365])
    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    content.extend([info_table, Spacer(1, 18)])

    def add_basket(title, courses, header_color):
        rows = [["Preference", "Course Name"]]
        for index, course in enumerate(courses, start=1):
            rows.append([str(index), Paragraph(html.escape(str(course)), course_style)])
        table = Table(rows, colWidths=[85, 415], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("BACKGROUND", (0, 0), (-1, 0), header_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        content.append(
            KeepTogether(
                [
                    Paragraph(title, styles["Heading2"]),
                    table,
                    Spacer(1, 16),
                ]
            )
        )

    add_basket("Basket 1 Preferences", basket1, colors.HexColor("#2563eb"))
    add_basket("Basket 2 Preferences", basket2, colors.HexColor("#be185d"))
    content.append(Paragraph("This is a system-generated submission report.", styles["Italic"]))
    document.build(content)
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------------------
# EXCEL EXPORT
# ---------------------------------------------------------------------

def make_excel_export(frame: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Faculty Preferences")
        ws = writer.sheets["Faculty Preferences"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for column_cells in ws.columns:
            max_length = max(
                (len(str(cell.value)) if cell.value is not None else 0)
                for cell in column_cells
            )
            ws.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 42)
    output.seek(0)
    return output.getvalue()


# ---------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------

defaults = {
    "b1": [],
    "b2": [],
    "submitted_emp": None,
    "pdf_data": None,
    "pdf_filename": None,
    "submission_ref": None,
    "admin_authenticated": False,
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default


def clear_selection():
    st.session_state.b1 = []
    st.session_state.b2 = []


def move_item(basket_key: str, index: int, direction: int):
    items = list(st.session_state[basket_key])
    new_index = index + direction
    if 0 <= new_index < len(items):
        items[index], items[new_index] = items[new_index], items[index]
        st.session_state[basket_key] = items


def selection_validation(basket1: list[str], basket2: list[str]) -> list[str]:
    errors = []
    if len(basket1) != MAX_PREFERENCES:
        errors.append(f"Basket 1 must contain exactly {MAX_PREFERENCES} courses.")
    if len(basket2) != MAX_PREFERENCES:
        errors.append(f"Basket 2 must contain exactly {MAX_PREFERENCES} courses.")

    all_courses = [str(x).strip().casefold() for x in basket1 + basket2]
    if len(all_courses) != len(set(all_courses)):
        errors.append("A course cannot be selected more than once across the two baskets.")
    return errors


def show_preference_list(title: str, key: str, pink: bool, disabled: bool):
    selected = list(st.session_state[key])
    st.markdown(f"**{title} ({len(selected)} / {MAX_PREFERENCES})**")
    if not selected:
        st.caption("No courses selected yet.")
        return

    for index, course in enumerate(selected):
        col_text, col_up, col_down = st.columns([6, 0.7, 0.7], gap="small")
        css_class = "preference-row pink" if pink else "preference-row"
        safe_course = html.escape(str(course))
        first = '<span class="first-choice">FIRST CHOICE</span>' if index == 0 else ""
        with col_text:
            st.markdown(
                f'<div class="{css_class}"><span class="rank">{index + 1}</span>'
                f'<span>{safe_course}</span>{first}</div>',
                unsafe_allow_html=True,
            )
        with col_up:
            st.button(
                "↑",
                key=f"{key}_up_{index}",
                help="Move preference up",
                disabled=disabled or index == 0,
                on_click=move_item,
                args=(key, index, -1),
                use_container_width=True,
            )
        with col_down:
            st.button(
                "↓",
                key=f"{key}_down_{index}",
                help="Move preference down",
                disabled=disabled or index == len(selected) - 1,
                on_click=move_item,
                args=(key, index, 1),
                use_container_width=True,
            )


# ---------------------------------------------------------------------
# LOAD SOURCE DATA
# ---------------------------------------------------------------------

try:
    basket1_courses = load_courses("Basket1")
    basket2_courses = load_courses("Basket2")
    faculty = load_employees()
    if not basket1_courses or not basket2_courses:
        st.error("Course lists are empty. Please check the Basket1 and Basket2 worksheets.")
        st.stop()
except Exception as exc:
    st.error(f"Unable to load Google Sheets data: {exc}")
    st.info("Check the spreadsheet ID, worksheet names and service-account sharing permissions.")
    st.stop()

# ---------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🎓 Preference Portal")
    page = st.radio(
        "Navigation",
        ["Faculty Submission", "Admin Dashboard"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(f"Academic period: {SEMESTER_TITLE}")
    st.caption("Select your preferences carefully. Once submitted, they are locked.")

# ---------------------------------------------------------------------
# FACULTY SUBMISSION PAGE
# ---------------------------------------------------------------------

if page == "Faculty Submission":
    st.markdown("### Faculty verification")
    verify_col, details_col = st.columns([1, 2], gap="large")

    with verify_col:
        entered_emp_id = st.text_input(
            "Employee ID",
            placeholder="Enter your Employee ID",
            key="entered_emp_id",
        )
        emp_id = normalize_emp_id(entered_emp_id)

    faculty_row = faculty[faculty["EmpID"] == emp_id] if emp_id else pd.DataFrame()
    verified = not faculty_row.empty
    name = str(faculty_row.iloc[0]["Name"]) if verified else ""
    designation = str(faculty_row.iloc[0]["Designation"]) if verified else ""

    with details_col:
        if verified:
            st.success("Employee verified")
            st.markdown(
                f"**Name:** {html.escape(name)}  \n"
                f"**Designation:** {html.escape(designation)}"
            )
        elif emp_id:
            st.error("Employee ID not found. Please verify the ID with the SCORE office.")
        else:
            st.info("Enter your Employee ID to verify your faculty details.")

    just_submitted = bool(emp_id and st.session_state.submitted_emp == emp_id)
    already_submitted = False

    if verified and not just_submitted:
        try:
            already_submitted = emp_id in submitted_ids_live()
        except Exception as exc:
            st.error(f"Could not verify submission status from Google Sheets: {exc}")
            st.warning("Submission is disabled until the response sheet can be checked.")
            already_submitted = True

    if already_submitted:
        st.error("Preferences have already been submitted for this Employee ID.")
        st.info("If a correction is required, please contact the authorized administrator.")
    elif just_submitted:
        st.success("Your preferences have been submitted successfully.")
        st.caption(f"Submission reference: {st.session_state.submission_ref}")
        if st.session_state.pdf_data:
            st.download_button(
                "📄 Download your PDF report",
                data=st.session_state.pdf_data,
                file_name=st.session_state.pdf_filename or f"{emp_id}_preferences.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    st.divider()
    st.markdown("### Course preference selection")
    st.caption(
        "Choose exactly seven courses in each basket. The order of selection determines "
        "the preference ranking. Use the arrows in the summary to change the order."
    )

    form_disabled = not verified or already_submitted or just_submitted

    # Available choices are filtered against the opposite basket.
    selected_b1 = list(st.session_state.b1)
    selected_b2 = list(st.session_state.b2)
    b1_allowed = selected_b1 + [
        course for course in basket1_courses
        if course.casefold() not in {x.casefold() for x in selected_b2}
        and course.casefold() not in {x.casefold() for x in selected_b1}
    ]
    b2_allowed = selected_b2 + [
        course for course in basket2_courses
        if course.casefold() not in {x.casefold() for x in selected_b1}
        and course.casefold() not in {x.casefold() for x in selected_b2}
    ]

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<div class="basket-title basket-one">📘 Basket 1 — Select 7 Courses</div>', unsafe_allow_html=True)
            new_b1 = st.multiselect(
                "Search and select Basket 1 courses",
                options=b1_allowed,
                key="b1",
                max_selections=MAX_PREFERENCES,
                disabled=form_disabled,
                placeholder="Verify your Employee ID to begin",
                help="Select seven courses. Your selection order represents preference priority.",
            )
            st.progress(min(len(new_b1) / MAX_PREFERENCES, 1.0), text=f"{len(new_b1)} of 7 selected")

        with st.container(border=True):
            st.markdown('<div class="basket-title basket-two">📗 Basket 2 — Select 7 Courses</div>', unsafe_allow_html=True)
            new_b2 = st.multiselect(
                "Search and select Basket 2 courses",
                options=b2_allowed,
                key="b2",
                max_selections=MAX_PREFERENCES,
                disabled=form_disabled,
                placeholder="Verify your Employee ID to begin",
                help="Select seven courses. Your selection order represents preference priority.",
            )
            st.progress(min(len(new_b2) / MAX_PREFERENCES, 1.0), text=f"{len(new_b2)} of 7 selected")

    with right:
        with st.container(border=True):
            st.markdown('<div class="summary-title">📋 Live preference summary</div>', unsafe_allow_html=True)
            show_preference_list("Basket 1", "b1", False, form_disabled)
            st.divider()
            show_preference_list("Basket 2", "b2", True, form_disabled)

    validation_errors = selection_validation(st.session_state.b1, st.session_state.b2)
    if verified and not form_disabled and validation_errors:
        for error in validation_errors:
            st.warning(error)

    st.divider()
    submit_col, reset_col, info_col = st.columns([1.2, 0.8, 1.5])

    with submit_col:
        submit_clicked = st.button(
            "🚀 Submit Preferences",
            type="primary",
            disabled=form_disabled,
            use_container_width=True,
        )
    with reset_col:
        st.button(
            "↺ Clear selections",
            disabled=form_disabled,
            use_container_width=True,
            on_click=clear_selection,
        )
    with info_col:
        st.markdown(
            '<div class="small-note">Please review all 14 preferences before submitting. '
            'Submitted preferences cannot be changed by faculty.</div>',
            unsafe_allow_html=True,
        )

    if submit_clicked:
        errors = selection_validation(st.session_state.b1, st.session_state.b2)
        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                with st.spinner("Saving your preferences securely..."):
                    response_sheet = ensure_response_headers()

                    # Live duplicate check immediately before writing.
                    # Google Sheets append is not a transactional/atomic lock;
                    # admin should review duplicates if multiple simultaneous submits occur.
                    if emp_id in submitted_ids_live():
                        st.error("A submission already exists for this Employee ID. No new row was added.")
                        st.stop()

                    submitted_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
                    reference = f"FCP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

                    row = [
                        emp_id,
                        name,
                        designation,
                        *st.session_state.b1,
                        *st.session_state.b2,
                        submitted_at,
                        reference,
                    ]

                    response_sheet.append_row(
                        row,
                        value_input_option="USER_ENTERED",
                        insert_data_option="INSERT_ROWS",
                    )

                    # Verify that the row is present before showing success.
                    time.sleep(0.5)
                    saved_ids = submitted_ids_live()
                    if emp_id not in saved_ids:
                        raise RuntimeError(
                            "Google Sheets did not confirm the saved submission. "
                            "Please contact the administrator before trying again."
                        )

                    st.session_state.pdf_data = generate_pdf(
                        emp_id,
                        name,
                        designation,
                        list(st.session_state.b1),
                        list(st.session_state.b2),
                        submitted_at,
                        reference,
                    )
                    st.session_state.pdf_filename = f"{emp_id}_preferences_{SEMESTER_TITLE.replace('–', '-')}.pdf"
                    st.session_state.submitted_emp = emp_id
                    st.session_state.submission_ref = reference
                    st.success("Preferences submitted successfully.")
                    st.rerun()

            except Exception as exc:
                st.error(f"Submission could not be completed: {exc}")
                st.warning(
                    "Before retrying, check the Admin Dashboard or contact the administrator "
                    "to ensure that a row was not already saved."
                )

# ---------------------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------------------

elif page == "Admin Dashboard":
    st.markdown("### 🔐 Administrator access")
    admin_password = st.secrets.get("admin", {}).get("password", "")

    if not admin_password:
        st.error(
            "Admin password is not configured. Add [admin] password in Streamlit secrets."
        )
        st.stop()

    if not st.session_state.admin_authenticated:
        with st.form("admin_login_form"):
            entered_password = st.text_input("Admin password", type="password")
            login = st.form_submit_button("Sign in", type="primary")
        if login:
            if entered_password == admin_password:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect administrator password.")
        st.stop()

    top_a, top_b = st.columns([4, 1])
    with top_a:
        st.success("Administrator authenticated")
    with top_b:
        if st.button("Sign out", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

    try:
        responses = get_response_records()
    except Exception as exc:
        st.error(f"Unable to retrieve responses: {exc}")
        st.stop()

    total_faculty = len(faculty)
    submitted_set = (
        set(responses["EmpID"].map(normalize_emp_id))
        if not responses.empty and "EmpID" in responses.columns
        else set()
    )
    submitted_set.discard("")
    pending_ids = set(faculty["EmpID"]) - submitted_set
    submitted_count = len(submitted_set)
    pending_count = len(pending_ids)

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Total faculty", total_faculty)
    metric2.metric("Submitted", submitted_count)
    metric3.metric("Pending", pending_count)
    metric4.metric(
        "Submission rate",
        f"{(submitted_count / total_faculty * 100):.1f}%" if total_faculty else "0%",
    )

    st.progress(
        submitted_count / total_faculty if total_faculty else 0,
        text="Faculty submission progress",
    )

    tab_submitted, tab_pending, tab_course = st.tabs(
        ["Submitted faculty", "Pending faculty", "Course preference summary"]
    )

    with tab_submitted:
        if responses.empty:
            st.info("No faculty preferences have been submitted yet.")
        else:
            display_columns = [
                col for col in ["EmpID", "Name", "Designation", "SubmittedAt", "SubmissionRef"]
                if col in responses.columns
            ]
            st.dataframe(
                responses[display_columns],
                use_container_width=True,
                hide_index=True,
            )

    with tab_pending:
        pending_frame = faculty[faculty["EmpID"].isin(pending_ids)].copy()
        if pending_frame.empty:
            st.success("All faculty members have submitted their preferences.")
        else:
            st.dataframe(pending_frame, use_container_width=True, hide_index=True)

    with tab_course:
        if responses.empty:
            st.info("Course preference statistics will appear after submissions.")
        else:
            count_rows = []
            for basket_name, columns in [
                ("Basket 1", [f"Basket1_P{i}" for i in range(1, 8)]),
                ("Basket 2", [f"Basket2_P{i}" for i in range(1, 8)]),
            ]:
                existing_columns = [col for col in columns if col in responses.columns]
                if not existing_columns:
                    continue
                values = responses[existing_columns].astype(str).values.ravel().tolist()
                counts = pd.Series(
                    [x.strip() for x in values if x and x.strip() and x.lower() != "nan"]
                ).value_counts()
                for course, count in counts.items():
                    count_rows.append(
                        {"Basket": basket_name, "Course": course, "Faculty selections": int(count)}
                    )

            if count_rows:
                summary = pd.DataFrame(count_rows).sort_values(
                    ["Basket", "Faculty selections", "Course"],
                    ascending=[True, False, True],
                )
                st.dataframe(summary, use_container_width=True, hide_index=True)
                csv_bytes = summary.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ Download course summary CSV",
                    data=csv_bytes,
                    file_name="course_preference_summary.csv",
                    mime="text/csv",
                )
            else:
                st.info("No course selections found in the response sheet.")

    st.divider()
    st.markdown("### Export reports")
    export_left, export_right = st.columns(2)

    with export_left:
        if not responses.empty:
            excel_bytes = make_excel_export(responses)
            st.download_button(
                "📊 Download all preferences (Excel)",
                data=excel_bytes,
                file_name="Faculty_Preferences_Winter_2026_2027.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.button("📊 Download all preferences (Excel)", disabled=True, use_container_width=True)

    with export_right:
        pending_export = make_excel_export(
            faculty[faculty["EmpID"].isin(pending_ids)].copy()
        )
        st.download_button(
            "📋 Download pending faculty (Excel)",
            data=pending_export,
            file_name="Pending_Faculty_Winter_2026_2027.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.caption(
        "Admin dashboard data is read directly from Google Sheets. "
        "Course counts represent the number of selections, not confirmed teaching allocations."
    )

# ---------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------

st.markdown("---")
st.markdown(
    f'<div style="text-align:center;color:#64748b;font-size:12px;">'
    f'{html.escape(SYSTEM_TITLE)} · {html.escape(SEMESTER_TITLE)}'
    f'</div>',
    unsafe_allow_html=True,
)

