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
            )
            -----------------------------------------------'''
import io
import time
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
def get_submitted_ids():
    try:
        response_sheet = ss.worksheet("Responses")
        return [str(x).strip().upper() for x in response_sheet.col_values(1) if x]
    except Exception:
        return []

b1_courses = load_courses("Basket1")
b2_courses = load_courses("Basket2")
employees = load_employees()

# -----------------------------
# SIDEBAR: PASSWORD-PROTECTED ADMIN DASHBOARD
# -----------------------------
with st.sidebar:
    st.markdown("### 🔐 Coordinator Portal")
    with st.expander("Admin Dashboard"):
        admin_pwd = st.text_input("Admin Password", type="password")
        expected_pwd = st.secrets.get("admin_password", "admin123")

        if admin_pwd:
            if admin_pwd == expected_pwd:
                st.success("Access Granted")
                if st.button("🔄 Refresh Live Data"):
                    get_submitted_ids.clear()
                    st.rerun()

                submitted_list = get_submitted_ids()
                # Exclude header row if present
                valid_submitted = [eid for eid in submitted_list if eid in set(employees["EmpID"])]
                total_faculty = len(employees)

                st.metric("Submissions", f"{len(valid_submitted)} / {total_faculty}")
                if total_faculty > 0:
                    st.progress(min(len(valid_submitted) / total_faculty, 1.0))

                # Pending Faculty List
                pending_df = employees[~employees["EmpID"].isin(valid_submitted)]
                st.markdown(f"**⏳ Pending Faculty ({len(pending_df)})**")
                if not pending_df.empty:
                    st.dataframe(pending_df[["EmpID", pending_df.columns[1]]], hide_index=True, use_container_width=True)
                else:
                    st.info("All faculty have submitted!")

                # Export Full Responses CSV
                try:
                    resp_records = ss.worksheet("Responses").get_all_values()
                    if len(resp_records) > 1:
                        resp_df = pd.DataFrame(resp_records[1:], columns=resp_records[0])
                        st.download_button(
                            "📥 Download All Responses (CSV)",
                            data=resp_df.to_csv(index=False).encode("utf-8"),
                            file_name="winter_2026_2027_responses.csv",
                            mime="text/csv",
                        )
                except Exception as err:
                    st.caption(f"Responses preview unavailable: {err}")
            else:
                st.error("Incorrect Password")

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
# GOOGLE SHEETS WRITE WITH RETRY BACKOFF
# -----------------------------
def submit_with_retry(emp_id, name, designation, b1, b2):
    response_sheet = ss.worksheet("Responses")
    max_retries = 3

    for attempt in range(max_retries):
        try:
            # Real-time duplicate check right before writing
            live_ids = [str(x).strip().upper() for x in response_sheet.col_values(1) if x]
            if emp_id in live_ids:
                return False, "duplicate", None

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            response_sheet.append_row([
                emp_id,
                name,
                designation,
                *b1,
                *b2,
                timestamp,
            ])
            return True, "ok", timestamp
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
            else:
                return False, str(e), None

# -----------------------------
# CONFIRMATION DIALOG
# -----------------------------
@st.dialog("Confirm Your Course Preferences", width="large")
def confirm_submission_dialog(emp_id, name, designation):
    st.markdown(f"**Employee:** {name} (`{emp_id}`) — *{designation}*")
    st.warning("⚠️ Once locked, preferences cannot be modified. Please verify your exact ranking:")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📘 Basket 1 Ranking**")
        for i, c in enumerate(st.session_state.b1, 1):
            st.markdown(f"**#{i}.** {c}")
    with c2:
        st.markdown("**📗 Basket 2 Ranking**")
        for i, c in enumerate(st.session_state.b2, 1):
            st.markdown(f"**#{i}.** {c}")

    st.divider()
    btn_confirm, btn_cancel = st.columns(2)

    with btn_confirm:
        if st.button("✅ Confirm & Lock Submission", type="primary", use_container_width=True):
            with st.spinner("Saving to Google Sheets..."):
                success, msg, timestamp = submit_with_retry(
                    emp_id, name, designation, st.session_state.b1, st.session_state.b2
                )

            if success:
                st.session_state.pdf_buffer = generate_pdf(
                    emp_id, name, designation, st.session_state.b1, st.session_state.b2, timestamp
                )
                st.session_state.submitted_emp = emp_id
                get_submitted_ids.clear()
                st.rerun()
            elif msg == "duplicate":
                st.error("🚫 Preferences were already submitted for this Employee ID.")
            else:
                st.error(f"Submission failed after retries: {msg}")

    with btn_cancel:
        if st.button("✏️ Go Back & Edit", use_container_width=True):
            st.rerun()

# -----------------------------
# SESSION STATE INIT
# -----------------------------
for key, default in [
    ("b1", []),
    ("b2", []),
    ("pdf_buffer", None),
    ("submitted_emp", None),
    ("last_emp_id", ""),
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
# TITLE
# -----------------------------
st.markdown(
    "<div class='title'>🎓 Faculty Course Preference System Winter 2026-2027</div>",
    unsafe_allow_html=True,
)

# -----------------------------
# STEP 1: EMP INPUT + DETAILS
# -----------------------------
with st.container(border=True):
    col_emp, col_details = st.columns([1, 2], gap="large")

    with col_emp:
        emp_id = st.text_input("Enter Employee ID", placeholder="Type your Employee ID...").strip().upper()

    # Reset selections if a different Employee ID is typed
    if st.session_state.last_emp_id != emp_id:
        st.session_state.b1 = []
        st.session_state.b2 = []
        st.session_state.pdf_buffer = None
        st.session_state.last_emp_id = emp_id

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
# DUPLICATE CHECK
# -----------------------------
is_just_submitted = bool(emp_id and st.session_state.submitted_emp == emp_id)

if emp_id and not is_just_submitted:
    if emp_id in get_submitted_ids():
        st.error("🚫 Preferences have already been submitted for this Employee ID.")
        st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# STEP 2: SPLIT-VIEW COURSE SELECTION + REORDERABLE SUMMARY
# -----------------------------
form_disabled = (name is None) or is_just_submitted

# Cross-basket duplicate prevention
available_b1 = [c for c in b1_courses if c not in st.session_state.b2]
available_b2 = [c for c in b2_courses if c not in st.session_state.b1]

left_col, right_col = st.columns([1.45, 1], gap="large")

with left_col:
    with st.container(border=True):
        st.markdown("<div class='basket1'>📘 Basket 1 — Select 7 Courses</div>", unsafe_allow_html=True)
        st.multiselect(
            "Search and pick 7 courses (1st choice first):",
            available_b1,
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
            available_b2,
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
# STEP 3: REVIEW & SUBMIT + DOWNLOAD
# -----------------------------
with st.container(border=True):
    col_submit, col_download, col_status = st.columns([1, 1, 1], gap="medium")

    with col_submit:
        submit_clicked = st.button("🚀 Review & Submit Preferences", type="primary", disabled=form_disabled)

    if submit_clicked:
        if len(st.session_state.b1) != 7 or len(st.session_state.b2) != 7:
            with col_status:
                st.error("⚠️ Select exactly 7 courses in both baskets.")
        else:
            confirm_submission_dialog(emp_id, name, designation)

    if is_just_submitted and st.session_state.pdf_buffer:
        with col_status:
            st.success("🎉 Submitted & Locked!")
        with col_download:
            st.download_button(
                "📄 Download PDF Report",
                data=st.session_state.pdf_buffer,
                file_name=f"{emp_id}_preferences.pdf",
                mime="application/pdf",
            )
           

