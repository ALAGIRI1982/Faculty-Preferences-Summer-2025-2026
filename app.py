import io
import threading
import time
from datetime import datetime
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from openpyxl.styles import Border, Font, PatternFill, Side

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
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    color: #0f172a;
}
.course-pill-b2 {
    background-color: #fdf2f8;
    border-left: 4px solid #ec4899;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    color: #0f172a;
}
/* Primary Submit / Confirm Button */
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
/* Action Buttons (Up / Down / Delete / Clear / Course Rows) */
div[data-testid="stButton"] > button[kind="secondary"] {
    padding: 6px 8px !important;
    min-height: 38px !important;
    width: 100% !important;
    font-size: 14px !important;
    line-height: 1.2 !important;
    border-radius: 8px !important;
    border: 1px solid #cbd5e1 !important;
    background-color: #ffffff !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover:not(:disabled) {
    border-color: #3b82f6 !important;
    background-color: #eff6ff !important;
}
/* Left-align full-width course row buttons inside the scrollable course lists */
div[data-testid="stVerticalBlock"] div[style*="overflow"] div[data-testid="stButton"] > button[kind="secondary"] {
    justify-content: flex-start !important;
    text-align: left !important;
    padding-left: 14px !important;
}
div[data-testid="stVerticalBlock"] div[style*="overflow"] div[data-testid="stButton"] > button[kind="secondary"] div,
div[data-testid="stVerticalBlock"] div[style*="overflow"] div[data-testid="stButton"] > button[kind="secondary"] p {
    text-align: left !important;
    width: 100% !important;
}
/* Download Button */
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
# GOOGLE SHEETS AUTH & THREAD LOCK
# -----------------------------
SPREADSHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"

@st.cache_resource
def get_write_lock():
    return threading.Lock()

write_lock = get_write_lock()

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
# PERSISTENT PORTAL MODE (GOOGLE SHEETS "Settings" TAB)
# -----------------------------
@st.cache_data(ttl=15)
def get_portal_mode():
    """Reads OPEN / CLOSED state from Google Sheets 'Settings' tab so it persists across restarts."""
    try:
        try:
            settings_ws = ss.worksheet("Settings")
        except gspread.WorksheetNotFound:
            settings_ws = ss.add_worksheet(title="Settings", rows=5, cols=2)
            settings_ws.update("A1:B1", [["Portal_Mode", "OPEN"]])
            return True
        val = settings_ws.acell("B1").value
        return str(val).strip().upper() != "CLOSED"
    except Exception:
        return True

def set_portal_mode(is_open: bool):
    """Updates OPEN / CLOSED state in Google Sheets 'Settings' tab and clears cache."""
    mode_str = "OPEN" if is_open else "CLOSED"
    try:
        settings_ws = ss.worksheet("Settings")
    except gspread.WorksheetNotFound:
        settings_ws = ss.add_worksheet(title="Settings", rows=5, cols=2)
    settings_ws.update("A1:B1", [["Portal_Mode", mode_str]])
    get_portal_mode.clear()

# -----------------------------
# DATA LOADERS (CACHED)
# -----------------------------
@st.cache_data(ttl=300)
def load_courses(sheet_name):
    sheet = ss.worksheet(sheet_name)
    data = sheet.get_all_values()
    if not data or len(data) < 2:
        return []
    return [str(row[0]).strip() for row in data[1:] if row and str(row[0]).strip()]

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
    df["EmpID"] = df[emp_col].astype(str).str.strip().str.upper()
    return df

@st.cache_data(ttl=15)
def get_all_responses():
    try:
        response_sheet = ss.worksheet("Responses")
        return response_sheet.get_all_values()
    except Exception:
        return []

def get_submitted_map():
    """Returns dict mapping uppercase EmpID -> full row from Responses."""
    records = get_all_responses()
    sub_map = {}
    for row in records[1:]:
        if row and str(row[0]).strip():
            eid = str(row[0]).strip().upper()
            sub_map[eid] = row
    return sub_map

b1_courses = load_courses("Basket1")
b2_courses = load_courses("Basket2")
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
# HELPER: STYLED EXCEL BUILDERS (RESPONSES & COURSE DEMAND)
# -----------------------------
def style_and_export_excel(df, sheet_name):
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]

        header_fill = PatternFill(start_color="548235", end_color="548235", fill_type="solid")
        row_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = Font(bold=True, color="FFFFFF")
            cell.border = thin_border

        for r_idx in range(2, len(df) + 2):
            for c_idx in range(1, len(df.columns) + 1):
                c = ws.cell(row=r_idx, column=c_idx)
                c.fill = row_fill
                c.border = thin_border

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_len + 4

    excel_buffer.seek(0)
    return excel_buffer

def build_admin_excel(resp_records):
    long_rows = []
    for row in resp_records[1:]:
        if len(row) < 17:
            continue
        e_id, e_name, e_desig = row[0].strip(), row[1].strip(), row[2].strip()
        b1_list = row[3:10]
        b2_list = row[10:17]

        for pref_num, course in enumerate(b1_list, 1):
            if str(course).strip():
                long_rows.append({
                    "EmpID": e_id,
                    "Name": e_name,
                    "Designation": e_desig,
                    "Attribute": f"B1P{pref_num}",
                    "Value": str(course).strip(),
                })
        for pref_num, course in enumerate(b2_list, 1):
            if str(course).strip():
                long_rows.append({
                    "EmpID": e_id,
                    "Name": e_name,
                    "Designation": e_desig,
                    "Attribute": f"B2P{pref_num}",
                    "Value": str(course).strip(),
                })

    export_df = pd.DataFrame
