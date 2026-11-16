'''import io
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
/* Left-align full-width course row buttons inside the scrollable course containers */
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] > button[kind="secondary"] p {
    text-align: left !important;
    width: 100%;
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

    export_df = pd.DataFrame(long_rows, columns=["EmpID", "Name", "Designation", "Attribute", "Value"])
    excel_buffer = style_and_export_excel(export_df, "Preferences")
    return export_df, excel_buffer

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

                # Dynamic Mode Toggle (Accept Preference Mode vs Non-Accept Preference Mode)
                current_mode_open = get_portal_mode()
                toggle_label = (
                    "🟢 Mode: Accept Preference Mode"
                    if current_mode_open
                    else "🔴 Mode: Non-Accept Preference Mode"
                )
                new_mode_open = st.toggle(
                    toggle_label,
                    value=current_mode_open,
                    key="admin_mode_toggle",
                )

                if new_mode_open != current_mode_open:
                    with st.spinner("Updating portal mode..."):
                        set_portal_mode(new_mode_open)
                    st.rerun()

                if get_portal_mode():
                    st.success("Status: **ACCEPTING PREFERENCES** (Faculty can submit)")
                else:
                    st.error("Status: **NON-ACCEPT MODE** (Form locked; PDF re-download only)")

                if st.button("🔄 Refresh Live Data", use_container_width=True):
                    get_all_responses.clear()
                    load_employees.clear()
                    get_portal_mode.clear()
                    st.rerun()

                resp_records = get_all_responses()
                raw_resp_ids = [
                    str(r[0]).strip().upper()
                    for r in resp_records[1:]
                    if r and str(r[0]).strip()
                ]
                faculty_ids = list(employees["EmpID"])
                faculty_set = set(faculty_ids)

                valid_submitted = set(raw_resp_ids) & faculty_set
                total_faculty = len(faculty_set)

                st.metric("Total Responses", f"{len(raw_resp_ids)} / {total_faculty}")
                if total_faculty > 0:
                    st.progress(min(len(valid_submitted) / total_faculty, 1.0))

                st.caption(
                    f"📄 Responses: {len(raw_resp_ids)} rows ({len(set(raw_resp_ids))} unique) | "
                    f"📋 Faculty List: {len(faculty_ids)} rows ({total_faculty} unique)"
                )

                not_in_faculty = set(raw_resp_ids) - faculty_set
                if not_in_faculty:
                    st.error(f"🚨 In Responses but NOT in Faculty List: {', '.join(sorted(not_in_faculty))}")

                if len(raw_resp_ids) != len(set(raw_resp_ids)):
                    dupes = {x for x in raw_resp_ids if raw_resp_ids.count(x) > 1}
                    st.warning(f"⚠️ Duplicate IDs in Responses: {', '.join(sorted(dupes))}")

                # Pending Faculty Table
                pending_df = employees[~employees["EmpID"].isin(valid_submitted)]
                st.markdown(f"**⏳ Pending Faculty ({len(pending_df)})**")
                if not pending_df.empty:
                    st.dataframe(
                        pending_df[["EmpID", pending_df.columns[1]]],
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.info("All faculty have submitted!")

                # Export & Course Demand Analytics
                if len(resp_records) > 1:
                    export_df, excel_buffer = build_admin_excel(resp_records)
                    st.download_button(
                        "📊 Download All Responses (.xlsx)",
                        data=excel_buffer,
                        file_name="winter_2026_2027_responses.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

                    if not export_df.empty:
                        st.markdown("**📈 Course Demand Summary**")
                        p1_counts = (
                            export_df[export_df["Attribute"].isin(["B1P1", "B2P1"])]
                            .groupby("Value")
                            .size()
                            .rename("#1 Picks")
                        )
                        total_counts = export_df.groupby("Value").size().rename("Total Picks")
                        demand_df = (
                            pd.concat([p1_counts, total_counts], axis=1)
                            .fillna(0)
                            .astype(int)
                            .sort_values(by=["#1 Picks", "Total Picks"], ascending=False)
                            .reset_index()
                            .rename(columns={"Value": "Course"})
                        )
                        st.dataframe(demand_df, hide_index=True, use_container_width=True)

                        demand_excel_buffer = style_and_export_excel(demand_df, "Course_Demand")
                        st.download_button(
                            "📥 Download Course Demand (.xlsx)",
                            data=demand_excel_buffer,
                            file_name="winter_2026_2027_course_demand.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
            else:
                st.error("Incorrect Password")

# -----------------------------
# THREAD-SAFE GOOGLE SHEETS WRITE WITH RETRY BACKOFF
# -----------------------------
def submit_with_retry(emp_id, name, designation, b1, b2):
    response_sheet = ss.worksheet("Responses")
    max_retries = 3

    with write_lock:
        if not get_portal_mode():
            return False, "closed", None

        for attempt in range(max_retries):
            try:
                live_ids = [str(x).strip().upper() for x in response_sheet.col_values(1) if x]
                if emp_id in live_ids:
                    return False, "duplicate", None

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                response_sheet.append_row(
                    [
                        f"'{emp_id}",
                        name,
                        designation,
                        *b1,
                        *b2,
                        timestamp,
                    ],
                    value_input_option="USER_ENTERED",
                )
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
                get_all_responses.clear()
                st.rerun(scope="app")
            elif msg == "duplicate":
                st.error("🚫 Preferences were already submitted for this Employee ID.")
            elif msg == "closed":
                st.error("🔒 Submissions were just closed by the Coordinator.")
            else:
                st.error(f"Submission failed after retries: {msg}")

    with btn_cancel:
        if st.button("✏️ Go Back & Edit", use_container_width=True):
            st.rerun()

# -----------------------------
# SESSION STATE & LIST ACTIONS
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

def add_course(basket_key, course):
    if course not in st.session_state[basket_key] and len(st.session_state[basket_key]) < 7:
        st.session_state[basket_key].append(course)

def remove_course(basket_key, index):
    if 0 <= index < len(st.session_state[basket_key]):
        st.session_state[basket_key].pop(index)

def clear_basket(basket_key):
    st.session_state[basket_key] = []

def move_item(basket_key, index, direction):
    items = list(st.session_state[basket_key])
    new_idx = index + direction
    if 0 <= new_idx < len(items):
        items[index], items[new_idx] = items[new_idx], items[index]
        st.session_state[basket_key] = items

# -----------------------------
# TITLE & LIVE PORTAL STATUS BANNER
# -----------------------------
portal_is_open = get_portal_mode()

st.markdown(
    "<div class='title'>🎓 Faculty Course Preference System Winter 2026-2027</div>",
    unsafe_allow_html=True,
)

if portal_is_open:
    st.success("🟢 **Accept Preference Mode:** Portal is OPEN for course preference submissions.")
else:
    st.error("🔴 **Non-Accept Preference Mode:** Portal is CLOSED for new submissions. Enter your Employee ID below to view or re-download your submitted PDF receipt.")

# -----------------------------
# STEP 1: EMP INPUT + DETAILS
# -----------------------------
with st.container(border=True):
    col_emp, col_details = st.columns([1, 2], gap="large")

    with col_emp:
        emp_id = st.text_input("Enter Employee ID", placeholder="Type your Employee ID...").strip().upper()

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
# ALREADY-SUBMITTED CHECK + SELF-SERVICE PDF RE-DOWNLOAD
# -----------------------------
is_just_submitted = bool(emp_id and st.session_state.submitted_emp == emp_id)

if emp_id and not is_just_submitted:
    submitted_map = get_submitted_map()
    if emp_id in submitted_map:
        existing_row = submitted_map[emp_id]
        st.info("🔒 Preferences have already been submitted and locked for this Employee ID.")

        if len(existing_row) >= 17:
            saved_name = existing_row[1] or (name or "")
            saved_desig = existing_row[2] or (designation or "")
            saved_b1 = existing_row[3:10]
            saved_b2 = existing_row[10:17]
            saved_ts = existing_row[17] if len(existing_row) > 17 else "Recorded"

            c_b1_view, c_b2_view = st.columns(2)
            with c_b1_view:
                st.markdown("**📘 Your Submitted Basket 1 Ranking**")
                for idx, c in enumerate(saved_b1, 1):
                    st.markdown(f"<div class='course-pill'><b>#{idx}</b> &nbsp; {c}</div>", unsafe_allow_html=True)
            with c_b2_view:
                st.markdown("**📗 Your Submitted Basket 2 Ranking**")
                for idx, c in enumerate(saved_b2, 1):
                    st.markdown(f"<div class='course-pill-b2'><b>#{idx}</b> &nbsp; {c}</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            reprint_pdf = generate_pdf(emp_id, saved_name, saved_desig, saved_b1, saved_b2, saved_ts)
            st.download_button(
                "📄 Re-Download Submitted PDF Receipt",
                data=reprint_pdf,
                file_name=f"{emp_id}_preferences.pdf",
                mime="application/pdf",
            )
        st.stop()

# -----------------------------
# NON-ACCEPT PREFERENCE MODE GUARD (FOR UNSUBMITTED FACULTY)
# -----------------------------
if not portal_is_open:
    if emp_id and name is not None:
        st.error(
            "🙏 **Submission Window Closed:** We could not find a recorded preference for your Employee ID, and online submissions are now closed. "
            "Please contact the **TT Coordinator**, who will be happy to assist you."
        )
    st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# STEP 2: FULL-WIDTH CLICKABLE COURSE ROWS (LEFT) + SUMMARY (RIGHT)
# -----------------------------
form_disabled = (name is None) or is_just_submitted

available_b1 = [c for c in b1_courses if c not in st.session_state.b1 and c not in st.session_state.b2]
available_b2 = [c for c in b2_courses if c not in st.session_state.b2 and c not in st.session_state.b1]

left_col, right_col = st.columns([1.3, 1.15], gap="large")

with left_col:
    # BASKET 1 CLICKABLE COURSE LIST
    with st.container(border=True):
        st.markdown("<div class='basket1'>📘 Basket 1 — Click Any Course to Add (Pick 7)</div>", unsafe_allow_html=True)
        search_b1 = st.text_input(
            "Search Basket 1",
            placeholder="🔍 Filter Basket 1 courses...",
            label_visibility="collapsed",
            disabled=form_disabled,
        )
        filtered_b1 = [c for c in available_b1 if search_b1.lower() in c.lower()]
        b1_full = len(st.session_state.b1) >= 7

        with st.container(height=270, border=False):
            if not filtered_b1:
                st.caption("No matching courses available.")
            else:
                for idx, course in enumerate(filtered_b1):
                    st.button(
                        f"➕  {course}",
                        key=f"add_b1_{idx}_{course}",
                        disabled=(form_disabled or b1_full),
                        on_click=add_course,
                        args=("b1", course),
                        use_container_width=True,
                    )

        st.progress(len(st.session_state.b1) / 7, text=f"Basket 1 Progress: {len(st.session_state.b1)} / 7 selected")

    st.markdown("<br>", unsafe_allow_html=True)

    # BASKET 2 CLICKABLE COURSE LIST
    with st.container(border=True):
        st.markdown("<div class='basket2'>📗 Basket 2 — Click Any Course to Add (Pick 7)</div>", unsafe_allow_html=True)
        search_b2 = st.text_input(
            "Search Basket 2",
            placeholder="🔍 Filter Basket 2 courses...",
            label_visibility="collapsed",
            disabled=form_disabled,
        )
        filtered_b2 = [c for c in available_b2 if search_b2.lower() in c.lower()]
        b2_full = len(st.session_state.b2) >= 7

        with st.container(height=270, border=False):
            if not filtered_b2:
                st.caption("No matching courses available.")
            else:
                for idx, course in enumerate(filtered_b2):
                    st.button(
                        f"➕  {course}",
                        key=f"add_b2_{idx}_{course}",
                        disabled=(form_disabled or b2_full),
                        on_click=add_course,
                        args=("b2", course),
                        use_container_width=True,
                    )

        st.progress(len(st.session_state.b2) / 7, text=f"Basket 2 Progress: {len(st.session_state.b2)} / 7 selected")

with right_col:
    with st.container(border=True):
        st.markdown("<div class='summary-header'>📋 Live Preference Summary (Rank & Manage)</div>", unsafe_allow_html=True)

        # Basket 1 Header + Clear All
        h1_title, h1_clear = st.columns([3.5, 1.5], gap="small")
        with h1_title:
            st.markdown(f"**📘 Basket 1 ({len(st.session_state.b1)} / 7)**")
        with h1_clear:
            st.button(
                "🔄 Clear",
                key="clear_b1_btn",
                disabled=(not st.session_state.b1 or form_disabled),
                on_click=clear_basket,
                args=("b1",),
                use_container_width=True,
            )

        if st.session_state.b1:
            for idx, course in enumerate(st.session_state.b1):
                c_text, c_up, c_down, c_del = st.columns([5.0, 1.0, 1.0, 1.0], gap="small")
                with c_text:
                    st.markdown(f"<div class='course-pill'><b>#{idx+1}</b> &nbsp; {course}</div>", unsafe_allow_html=True)
                with c_up:
                    st.button(
                        "⬆️",
                        key=f"b1_up_{idx}",
                        disabled=(idx == 0 or form_disabled),
                        on_click=move_item,
                        args=("b1", idx, -1),
                        use_container_width=True,
                    )
                with c_down:
                    st.button(
                        "⬇️",
                        key=f"b1_dn_{idx}",
                        disabled=(idx == len(st.session_state.b1) - 1 or form_disabled),
                        on_click=move_item,
                        args=("b1", idx, 1),
                        use_container_width=True,
                    )
                with c_del:
                    st.button(
                        "🗑️",
                        key=f"b1_del_{idx}",
                        disabled=form_disabled,
                        on_click=remove_course,
                        args=("b1", idx),
                        use_container_width=True,
                    )
        else:
            st.caption("Click any course on the left to add it to Basket 1.")

        st.divider()

        # Basket 2 Header + Clear All
        h2_title, h2_clear = st.columns([3.5, 1.5], gap="small")
        with h2_title:
            st.markdown(f"**📗 Basket 2 ({len(st.session_state.b2)} / 7)**")
        with h2_clear:
            st.button(
                "🔄 Clear",
                key="clear_b2_btn",
                disabled=(not st.session_state.b2 or form_disabled),
                on_click=clear_basket,
                args=("b2",),
                use_container_width=True,
            )

        if st.session_state.b2:
            for idx, course in enumerate(st.session_state.b2):
                c_text, c_up, c_down, c_del = st.columns([5.0, 1.0, 1.0, 1.0], gap="small")
                with c_text:
                    st.markdown(f"<div class='course-pill-b2'><b>#{idx+1}</b> &nbsp; {course}</div>", unsafe_allow_html=True)
                with c_up:
                    st.button(
                        "⬆️",
                        key=f"b2_up_{idx}",
                        disabled=(idx == 0 or form_disabled),
                        on_click=move_item,
                        args=("b2", idx, -1),
                        use_container_width=True,
                    )
                with c_down:
                    st.button(
                        "⬇️",
                        key=f"b2_dn_{idx}",
                        disabled=(idx == len(st.session_state.b2) - 1 or form_disabled),
                        on_click=move_item,
                        args=("b2", idx, 1),
                        use_container_width=True,
                    )
                with c_del:
                    st.button(
                        "🗑️",
                        key=f"b2_del_{idx}",
                        disabled=form_disabled,
                        on_click=remove_course,
                        args=("b2", idx),
                        use_container_width=True,
                    )
        else:
            st.caption("Click any course on the left to add it to Basket 2.")

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
            )-------------------''''
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
# TITLE (Render immediately so the page never appears blank)
# -----------------------------
st.markdown(
    "<div class='title'>🎓 Faculty Course Preference System Winter 2026-2027</div>",
    unsafe_allow_html=True,
)

# -----------------------------
# GOOGLE SHEETS AUTH & THREAD LOCK (Single cached resource)
# -----------------------------
SPREADSHEET_ID = "1y1a9UvWW-xrIBR7-hEWn70I7NmsSHpX3AEspg-PLXfg"

@st.cache_resource
def get_write_lock():
    return threading.Lock()

write_lock = get_write_lock()

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

try:
    ss = get_spreadsheet()
except Exception as e:
    st.error(f"Database connection error: {e}")
    st.stop()

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

    export_df = pd.DataFrame(long_rows, columns=["EmpID", "Name", "Designation", "Attribute", "Value"])
    excel_buffer = style_and_export_excel(export_df, "Preferences")
    return export_df, excel_buffer

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

                # Dynamic Mode Toggle (Accept Preference Mode vs Non-Accept Preference Mode)
                current_mode_open = get_portal_mode()
                toggle_label = (
                    "🟢 Mode: Accept Preference Mode"
                    if current_mode_open
                    else "🔴 Mode: Non-Accept Preference Mode"
                )
                new_mode_open = st.toggle(
                    toggle_label,
                    value=current_mode_open,
                    key="admin_mode_toggle",
                )

                if new_mode_open != current_mode_open:
                    with st.spinner("Updating portal mode..."):
                        set_portal_mode(new_mode_open)
                    st.rerun()

                if get_portal_mode():
                    st.success("Status: **ACCEPTING PREFERENCES** (Faculty can submit)")
                else:
                    st.error("Status: **NON-ACCEPT MODE** (Form locked; PDF re-download only)")

                if st.button("🔄 Refresh Live Data", use_container_width=True):
                    get_all_responses.clear()
                    load_employees.clear()
                    get_portal_mode.clear()
                    st.rerun()

                resp_records = get_all_responses()
                raw_resp_ids = [
                    str(r[0]).strip().upper()
                    for r in resp_records[1:]
                    if r and str(r[0]).strip()
                ]
                faculty_ids = list(employees["EmpID"])
                faculty_set = set(faculty_ids)

                valid_submitted = set(raw_resp_ids) & faculty_set
                total_faculty = len(faculty_set)

                st.metric("Total Responses", f"{len(raw_resp_ids)} / {total_faculty}")
                if total_faculty > 0:
                    st.progress(min(len(valid_submitted) / total_faculty, 1.0))

                st.caption(
                    f"📄 Responses: {len(raw_resp_ids)} rows ({len(set(raw_resp_ids))} unique) | "
                    f"📋 Faculty List: {len(faculty_ids)} rows ({total_faculty} unique)"
                )

                not_in_faculty = set(raw_resp_ids) - faculty_set
                if not_in_faculty:
                    st.error(f"🚨 In Responses but NOT in Faculty List: {', '.join(sorted(not_in_faculty))}")

                if len(raw_resp_ids) != len(set(raw_resp_ids)):
                    dupes = {x for x in raw_resp_ids if raw_resp_ids.count(x) > 1}
                    st.warning(f"⚠️ Duplicate IDs in Responses: {', '.join(sorted(dupes))}")

                # Pending Faculty Table
                pending_df = employees[~employees["EmpID"].isin(valid_submitted)]
                st.markdown(f"**⏳ Pending Faculty ({len(pending_df)})**")
                if not pending_df.empty:
                    st.dataframe(
                        pending_df[["EmpID", pending_df.columns[1]]],
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.info("All faculty have submitted!")

                # Export & Course Demand Analytics
                if len(resp_records) > 1:
                    export_df, excel_buffer = build_admin_excel(resp_records)
                    st.download_button(
                        "📊 Download All Responses (.xlsx)",
                        data=excel_buffer,
                        file_name="winter_2026_2027_responses.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

                    if not export_df.empty:
                        st.markdown("**📈 Course Demand Summary**")
                        p1_counts = (
                            export_df[export_df["Attribute"].isin(["B1P1", "B2P1"])]
                            .groupby("Value")
                            .size()
                            .rename("#1 Picks")
                        )
                        total_counts = export_df.groupby("Value").size().rename("Total Picks")
                        demand_df = (
                            pd.concat([p1_counts, total_counts], axis=1)
                            .fillna(0)
                            .astype(int)
                            .sort_values(by=["#1 Picks", "Total Picks"], ascending=False)
                            .reset_index()
                            .rename(columns={"Value": "Course"})
                        )
                        st.dataframe(
                            demand_df,
                            hide_index=True,
                            use_container_width=True,
                        )

                        demand_excel_buffer = style_and_export_excel(demand_df, "Course_Demand")
                        st.download_button(
                            "📥 Download Course Demand (.xlsx)",
                            data=demand_excel_buffer,
                            file_name="winter_2026_2027_course_demand.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
            else:
                st.error("Incorrect Password")

# -----------------------------
# THREAD-SAFE GOOGLE SHEETS WRITE WITH RETRY BACKOFF
# -----------------------------
def submit_with_retry(emp_id, name, designation, b1, b2):
    response_sheet = ss.worksheet("Responses")
    max_retries = 3

    with write_lock:
        if not get_portal_mode():
            return False, "closed", None

        for attempt in range(max_retries):
            try:
                live_ids = [str(x).strip().upper() for x in response_sheet.col_values(1) if x]
                if emp_id in live_ids:
                    return False, "duplicate", None

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                response_sheet.append_row(
                    [
                        f"'{emp_id}",
                        name,
                        designation,
                        *b1,
                        *b2,
                        timestamp,
                    ],
                    value_input_option="USER_ENTERED",
                )
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
                get_all_responses.clear()
                st.rerun(scope="app")
            elif msg == "duplicate":
                st.error("🚫 Preferences were already submitted for this Employee ID.")
            elif msg == "closed":
                st.error("🔒 Submissions were just closed by the Coordinator.")
            else:
                st.error(f"Submission failed after retries: {msg}")

    with btn_cancel:
        if st.button("✏️ Go Back & Edit", use_container_width=True):
            st.rerun()

# -----------------------------
# SESSION STATE & LIST ACTIONS
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

def add_course(basket_key, course):
    if course not in st.session_state[basket_key] and len(st.session_state[basket_key]) < 7:
        st.session_state[basket_key].append(course)

def remove_course(basket_key, index):
    if 0 <= index < len(st.session_state[basket_key]):
        st.session_state[basket_key].pop(index)

def clear_basket(basket_key):
    st.session_state[basket_key] = []

def move_item(basket_key, index, direction):
    items = list(st.session_state[basket_key])
    new_idx = index + direction
    if 0 <= new_idx < len(items):
        items[index], items[new_idx] = items[new_idx], items[index]
        st.session_state[basket_key] = items

# -----------------------------
# LIVE PORTAL STATUS BANNER
# -----------------------------
portal_is_open = get_portal_mode()

if portal_is_open:
    st.success("🟢 **Accept Preference Mode:** Portal is OPEN for course preference submissions.")
else:
    st.error("🔴 **Non-Accept Preference Mode:** Portal is CLOSED for new submissions. Enter your Employee ID below to view or re-download your submitted PDF receipt.")

# -----------------------------
# STEP 1: EMP INPUT + DETAILS
# -----------------------------
with st.container(border=True):
    col_emp, col_details = st.columns([1, 2], gap="large")

    with col_emp:
        emp_id = st.text_input("Enter Employee ID", placeholder="Type your Employee ID...").strip().upper()

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
# ALREADY-SUBMITTED CHECK + SELF-SERVICE PDF RE-DOWNLOAD
# -----------------------------
is_just_submitted = bool(emp_id and st.session_state.submitted_emp == emp_id)

if emp_id and not is_just_submitted:
    submitted_map = get_submitted_map()
    if emp_id in submitted_map:
        existing_row = submitted_map[emp_id]
        st.info("🔒 Preferences have already been submitted and locked for this Employee ID.")

        if len(existing_row) >= 17:
            saved_name = existing_row[1] or (name or "")
            saved_desig = existing_row[2] or (designation or "")
            saved_b1 = existing_row[3:10]
            saved_b2 = existing_row[10:17]
            saved_ts = existing_row[17] if len(existing_row) > 17 else "Recorded"

            c_b1_view, c_b2_view = st.columns(2)
            with c_b1_view:
                st.markdown("**📘 Your Submitted Basket 1 Ranking**")
                for idx, c in enumerate(saved_b1, 1):
                    st.markdown(f"<div class='course-pill'><b>#{idx}</b> &nbsp; {c}</div>", unsafe_allow_html=True)
            with c_b2_view:
                st.markdown("**📗 Your Submitted Basket 2 Ranking**")
                for idx, c in enumerate(saved_b2, 1):
                    st.markdown(f"<div class='course-pill-b2'><b>#{idx}</b> &nbsp; {c}</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            reprint_pdf = generate_pdf(emp_id, saved_name, saved_desig, saved_b1, saved_b2, saved_ts)
            st.download_button(
                "📄 Re-Download Submitted PDF Receipt",
                data=reprint_pdf,
                file_name=f"{emp_id}_preferences.pdf",
                mime="application/pdf",
            )
        st.stop()

# -----------------------------
# NON-ACCEPT PREFERENCE MODE GUARD (FOR UNSUBMITTED FACULTY)
# -----------------------------
if not portal_is_open:
    if emp_id and name is not None:
        st.error(
            "🙏 **Submission Window Closed:** We could not find a recorded preference for your Employee ID, and online submissions are now closed. "
            "Please contact the **TT Coordinator**, who will be happy to assist you."
        )
    st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# STEP 2: FULL-WIDTH LEFT-ALIGNED CLICKABLE COURSE ROWS (LEFT) + SUMMARY (RIGHT)
# -----------------------------
form_disabled = (name is None) or is_just_submitted

available_b1 = [c for c in b1_courses if c not in st.session_state.b1 and c not in st.session_state.b2]
available_b2 = [c for c in b2_courses if c not in st.session_state.b2 and c not in st.session_state.b1]

left_col, right_col = st.columns([1.3, 1.15], gap="large")

with left_col:
    # BASKET 1 CLICKABLE COURSE LIST
    with st.container(border=True):
        st.markdown("<div class='basket1'>📘 Basket 1 — Click Any Course to Add (Pick 7)</div>", unsafe_allow_html=True)
        search_b1 = st.text_input(
            "Search Basket 1",
            placeholder="🔍 Filter Basket 1 courses...",
            label_visibility="collapsed",
            disabled=form_disabled,
        )
        filtered_b1 = [c for c in available_b1 if search_b1.lower() in c.lower()]
        b1_full = len(st.session_state.b1) >= 7

        with st.container(height=270, border=False):
            if not filtered_b1:
                st.caption("No matching courses available.")
            else:
                for idx, course in enumerate(filtered_b1):
                    st.button(
                        f"➕  {course}",
                        key=f"add_b1_{idx}_{course}",
                        disabled=(form_disabled or b1_full),
                        on_click=add_course,
                        args=("b1", course),
                        use_container_width=True,
                    )

        st.progress(len(st.session_state.b1) / 7, text=f"Basket 1 Progress: {len(st.session_state.b1)} / 7 selected")

    st.markdown("<br>", unsafe_allow_html=True)

    # BASKET 2 CLICKABLE COURSE LIST
    with st.container(border=True):
        st.markdown("<div class='basket2'>📗 Basket 2 — Click Any Course to Add (Pick 7)</div>", unsafe_allow_html=True)
        search_b2 = st.text_input(
            "Search Basket 2",
            placeholder="🔍 Filter Basket 2 courses...",
            label_visibility="collapsed",
            disabled=form_disabled,
        )
        filtered_b2 = [c for c in available_b2 if search_b2.lower() in c.lower()]
        b2_full = len(st.session_state.b2) >= 7

        with st.container(height=270, border=False):
            if not filtered_b2:
                st.caption("No matching courses available.")
            else:
                for idx, course in enumerate(filtered_b2):
                    st.button(
                        f"➕  {course}",
                        key=f"add_b2_{idx}_{course}",
                        disabled=(form_disabled or b2_full),
                        on_click=add_course,
                        args=("b2", course),
                        use_container_width=True,
                    )

        st.progress(len(st.session_state.b2) / 7, text=f"Basket 2 Progress: {len(st.session_state.b2)} / 7 selected")

with right_col:
    with st.container(border=True):
        st.markdown("<div class='summary-header'>📋 Live Preference Summary (Rank & Manage)</div>", unsafe_allow_html=True)

        # Basket 1 Header + Clear All
        h1_title, h1_clear = st.columns([3.5, 1.5], gap="small")
        with h1_title:
            st.markdown(f"**📘 Basket 1 ({len(st.session_state.b1)} / 7)**")
        with h1_clear:
            st.button(
                "🔄 Clear",
                key="clear_b1_btn",
                disabled=(not st.session_state.b1 or form_disabled),
                on_click=clear_basket,
                args=("b1",),
                use_container_width=True,
            )

        if st.session_state.b1:
            for idx, course in enumerate(st.session_state.b1):
                c_text, c_up, c_down, c_del = st.columns([5.0, 1.0, 1.0, 1.0], gap="small")
                with c_text:
                    st.markdown(f"<div class='course-pill'><b>#{idx+1}</b> &nbsp; {course}</div>", unsafe_allow_html=True)
                with c_up:
                    st.button(
                        "⬆️",
                        key=f"b1_up_{idx}",
                        disabled=(idx == 0 or form_disabled),
                        on_click=move_item,
                        args=("b1", idx, -1),
                        use_container_width=True,
                    )
                with c_down:
                    st.button(
                        "⬇️",
                        key=f"b1_dn_{idx}",
                        disabled=(idx == len(st.session_state.b1) - 1 or form_disabled),
                        on_click=move_item,
                        args=("b1", idx, 1),
                        use_container_width=True,
                    )
                with c_del:
                    st.button(
                        "🗑️",
                        key=f"b1_del_{idx}",
                        disabled=form_disabled,
                        on_click=remove_course,
                        args=("b1", idx),
                        use_container_width=True,
                    )
        else:
            st.caption("Click any course on the left to add it to Basket 1.")

        st.divider()

        # Basket 2 Header + Clear All
        h2_title, h2_clear = st.columns([3.5, 1.5], gap="small")
        with h2_title:
            st.markdown(f"**📗 Basket 2 ({len(st.session_state.b2)} / 7)**")
        with h2_clear:
            st.button(
                "🔄 Clear",
                key="clear_b2_btn",
                disabled=(not st.session_state.b2 or form_disabled),
                on_click=clear_basket,
                args=("b2",),
                use_container_width=True,
            )

        if st.session_state.b2:
            for idx, course in enumerate(st.session_state.b2):
                c_text, c_up, c_down, c_del = st.columns([5.0, 1.0, 1.0, 1.0], gap="small")
                with c_text:
                    st.markdown(f"<div class='course-pill-b2'><b>#{idx+1}</b> &nbsp; {course}</div>", unsafe_allow_html=True)
                with c_up:
                    st.button(
                        "⬆️",
                        key=f"b2_up_{idx}",
                        disabled=(idx == 0 or form_disabled),
                        on_click=move_item,
                        args=("b2", idx, -1),
                        use_container_width=True,
                    )
                with c_down:
                    st.button(
                        "⬇️",
                        key=f"b2_dn_{idx}",
                        disabled=(idx == len(st.session_state.b2) - 1 or form_disabled),
                        on_click=move_item,
                        args=("b2", idx, 1),
                        use_container_width=True,
                    )
                with c_del:
                    st.button(
                        "🗑️",
                        key=f"b2_del_{idx}",
                        disabled=form_disabled,
                        on_click=remove_course,
                        args=("b2", idx),
                        use_container_width=True,
                    )
        else:
            st.caption("Click any course on the left to add it to Basket 2.")

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
