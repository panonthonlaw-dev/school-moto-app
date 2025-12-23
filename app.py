import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz, random, os, base64, io, qrcode, glob, math, mimetypes, json, requests, re, textwrap, time, ast
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# PDF Libraries
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
except: pass
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import plotly.express as px

# ==========================================
# 1. INITIAL SETTINGS & SESSION STATE
# ==========================================
st.set_page_config(page_title="ระบบเจ้าหน้าที่ส่วนกลาง", page_icon="👮‍♂️", layout="wide")

# Session States (รวมของเดิมและของจราจร)
states = {
    'logged_in': False, 'user_info': {}, 'current_dept': None, 'current_user': None,
    'view_mode': 'list', 'selected_case_id': None, 'unlock_password': "",
    'page_pending': 1, 'page_finished': 1, 'search_query_main': "",
    'current_user_pwd': "", 'last_active': time.time(),
    # Traffic States
    'reset_count': 0, 'page': 'teacher', 'search_results_df': None, 
    'edit_data': None, 'officer_name': "", 'officer_role': ""
}
for key, val in states.items():
    if key not in st.session_state: st.session_state[key] = val

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "THSarabunNew.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "THSarabunNewBold.ttf")

# Config จราจร
SHEET_NAME_TRAFFIC = "Motorcycle_DB"
DRIVE_FOLDER_ID = "1WQGATGaGBoIjf44Yj_-DjuX8LZ8kbmBA"
UPGRADE_PASSWORD = st.secrets.get("UPGRADE_PASSWORD", "Patwitnext")
OFFICER_ACCOUNTS = st.secrets.get("OFFICER_ACCOUNTS", {})
GAS_APP_URL = "https://script.google.com/macros/s/AKfycbxRf6z032SxMkiI4IxtUBvWLKeo1LmIQAUMByoXidy4crNEwHoO6h0B-3hT0X7Q5g/exec"

# Logo System
LOGO_PATH = next((f for f in glob.glob(os.path.join(BASE_DIR, "school_logo*")) if os.path.isfile(f)), 
                 next((f for f in ["logo.png", "logo.jpg", "logo"] if os.path.exists(f)), None))
def get_base64_image(path):
    if not path or not os.path.exists(path): return ""
    with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
LOGO_BASE64 = get_base64_image(LOGO_PATH)

# Helpers
def get_now_th(): return datetime.now(pytz.timezone('Asia/Bangkok'))
def clean_val(val): return str(val).strip() if not pd.isna(val) else ""
def process_image(img_file):
    if not img_file: return ""
    try:
        img = Image.open(img_file).convert('RGB'); img.thumbnail((800, 800))
        buf = io.BytesIO(); img.save(buf, format="JPEG", quality=65); return base64.b64encode(buf.getvalue()).decode()
    except: return ""

def calculate_pagination(key, total_items, limit=5):
    if key not in st.session_state: st.session_state[key] = 1
    total_pages = math.ceil(total_items / limit) or 1
    if st.session_state[key] > total_pages: st.session_state[key] = 1
    start_idx = (st.session_state[key] - 1) * limit
    end_idx = start_idx + limit
    return start_idx, end_idx, st.session_state[key], total_pages

# ==========================================
# 2. MODULE: INVESTIGATION (ต้นฉบับ 100% ห้ามแก้)
# ==========================================
def create_pdf_inv(row):
    rid = str(row.get('Report_ID', '')); date_str = str(row.get('Timestamp', ''))
    audit_log = str(row.get('Audit_Log', '')); latest_date = "-"
    if audit_log:
        try:
            lines = [l for l in audit_log.split('\n') if l.strip()]
            if lines and '[' in lines[-1] and ']' in lines[-1]: latest_date = lines[-1][lines[-1].find('[')+1:lines[-1].find(']')]
        except: pass
    p_name = st.session_state.user_info.get('name', 'System'); p_time = get_now_th().strftime("%d/%m/%Y %H:%M:%S")
    qr = qrcode.make(rid); qi = io.BytesIO(); qr.save(qi, format="PNG"); qr_b64 = base64.b64encode(qi.getvalue()).decode()
    
    img_html = ""
    if clean_val(row.get('Evidence_Image')):
        img_html += f"<div style='text-align:center;margin-top:10px;'><b>พยานหลักฐาน</b><br><img src='data:image/jpeg;base64,{row.get('Evidence_Image')}' style='max-width:380px;max-height:220px;object-fit:contain;border:1px solid #ccc;'></div>"
    if clean_val(row.get('Image_Data')):
        img_html += f"<div style='text-align:center;margin-top:10px;'><b>ภาพประกอบเหตุการณ์</b><br><img src='data:image/jpeg;base64,{row.get('Image_Data')}' style='max-width:380px;max-height:220px;object-fit:contain;border:1px solid #ccc;'></div>"

    logo_html = f'<img class="logo" src="data:image/png;base64,{LOGO_BASE64}">' if LOGO_BASE64 else ""
    html_content = f"""
    <html><head><style>@font-face {{ font-family: 'THSarabunNew'; src: url('file://{FONT_FILE}'); }}
    @page {{ size: A4; margin: 2cm; @bottom-right {{ content: "ผู้พิมพ์: {p_name} | เวลา: {p_time} | หน้า " counter(page); font-family: 'THSarabunNew'; font-size: 12pt; }} }}
    body {{ font-family: 'THSarabunNew'; font-size: 16pt; line-height: 1.3; }}
    .header {{ text-align: center; position: relative; min-height: 80px; }} .logo {{ position: absolute; top: 0; left: 0; width: 60px; }}
    .qr {{ position: absolute; top: 0; right: 0; width: 60px; }} .box {{ border: 1px solid #000; background-color: #f9f9f9; padding: 10px; min-height: 50px; white-space: pre-wrap; }}
    .sig-table {{ width: 100%; margin-top: 30px; text-align: center; border-collapse: collapse; }} .sig-table td {{ padding-bottom: 25px; vertical-align: top; }}
    </style></head><body><div class="header">{logo_html}<div style="font-size: 22pt; font-weight: bold;">สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</div>
    <div style="font-size: 18pt;">ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน</div><img class="qr" src="data:image/png;base64,{qr_b64}"></div><hr>
    <table style="width:100%;"><tr><td width="60%"><b>เลขที่รับแจ้ง:</b> {rid}</td><td width="40%" style="text-align:right;"><b>วันที่แจ้ง:</b> {date_str}<br><b>วันที่บันทึกผล:</b> {latest_date}</td></tr></table>
    <p><b>ผู้แจ้ง:</b> {row.get('Reporter','-')} | <b>ประเภทเหตุ:</b> {row.get('Incident_Type','-')} | <b>สถานที่:</b> {row.get('Location','-')}</p>
    <div style="margin-top:10px;"><b>รายละเอียดเหตุการณ์:</b></div><div class="box">{row.get('Details','-')}</div>
    <div><b>ผลการดำเนินการสอบสวน:</b></div><div class="box">{row.get('Statement','-')}</div>{img_html}
    <table class="sig-table"><tr><td width="50%">ลงชื่อ..........................................................<br>( {row.get('Victim','')} )<br>ผู้เสียหาย</td><td width="50%">ลงชื่อ..........................................................<br>( {row.get('Accused','')} )<br>ผู้ถูกกล่าวหา</td></tr>
    <tr><td>ลงชื่อ..........................................................<br>( {row.get('Student_Police_Investigator','')} )<br>ตำรวจนักเรียนผู้สอบสวน</td><td>ลงชื่อ..........................................................<br>( {row.get('Witness','')} )<br>พยาน</td></tr>
    <tr><td colspan="2"><br>ลงชื่อ..........................................................<br>( {row.get('Teacher_Investigator','')} )<br>ครูผู้สอบสวน</td></tr></table></body></html>"""
    return HTML(string=html_content, base_url=BASE_DIR).write_pdf(font_config=FontConfiguration())

def investigation_module():
    st.session_state.current_user = st.session_state.user_info
    user = st.session_state.current_user
    st.sidebar.button("⬅️ กลับหน้าเลือกแผนก", on_click=lambda: setattr(st.session_state, 'current_dept', None), width='stretch')
    col_h1, col_h2, col_h3 = st.columns([1, 4, 1])
    with col_h1:
        if LOGO_PATH: st.image(LOGO_PATH, width=80)
    with col_h2:
        st.markdown(f"<div style='font-size: 26px; font-weight: bold; color: #1E3A8A; padding-top: 20px;'>🏢 ระบบสอบสวน คุณ{user['name']}</div>", unsafe_allow_html=True)
    with col_h3:
        if st.button("🔴 Logout", key="inv_logout", use_container_width=True): st.session_state.clear(); st.rerun()

    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_raw = conn.read(ttl="0")
        df_display = df_raw.copy().fillna("")
        for c in ['Report_ID', 'Timestamp', 'Reporter', 'Incident_Type', 'Location', 'Details', 'Status', 'Image_Data', 'Audit_Log', 'Victim', 'Accused', 'Witness', 'Teacher_Investigator', 'Student_Police_Investigator', 'Statement', 'Evidence_Image']:
            if c not in df_display.columns: df_display[c] = ""
        df_display['Report_ID'] = df_display['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        if st.session_state.view_mode == "list":
            tab_list, tab_dash = st.tabs(["📋 รายการแจ้งเหตุ", "📊 แดชบอร์ดสถิติ"])
            with tab_list:
                c_search, c_btn_search, c_btn_clear = st.columns([3, 1, 1])
                search_q = c_search.text_input("ค้นหา", placeholder="เลขเคส, ชื่อ, หรือเหตุการณ์...", key="search_query_main", label_visibility="collapsed")
                c_btn_search.button("🔍 ค้นหา", use_container_width=True)
                if c_btn_clear.button("❌ ล้าง", use_container_width=True): st.rerun()
                filtered = df_display.copy()
                if search_q: filtered = filtered[filtered.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]
                
                df_p = filtered[filtered['Status'].isin(["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ"])][::-1]
                df_f = filtered[filtered['Status'] == "ดำเนินการเรียบร้อย"][::-1]

                st.markdown("<h4 style='color:#1E3A8A; background-color:#f0f2f6; padding:10px; border-radius:5px;'>⏳ รายการที่รอการดำเนินการ</h4>", unsafe_allow_html=True)
                start_p, end_p, cur_p, tot_p = calculate_pagination('page_pending', len(df_p), 5)
                h1, h2, h3, h4 = st.columns([2.5, 2, 3, 1.5])
                h1.markdown("**เลขที่รับแจ้ง**"); h2.markdown("**วันเวลา**"); h3.markdown("**ประเภทเหตุ**"); h4.markdown("**สถานะ**")
                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                
                if df_p.empty: st.caption("ไม่มีรายการ")
                for i, row in df_p.iloc[start_p:end_p].iterrows():
                    cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                    with cc1: st.button(f"📝 {row['Report_ID']}", key=f"p_{i}", use_container_width=True, on_click=lambda r=row['Report_ID']: st.session_state.update({'selected_case_id': r, 'view_mode': 'detail', 'unlock_password': ""}))
                    cc2.write(row['Timestamp']); cc3.write(row['Incident_Type'])
                    cc4.markdown(f"<span style='color:orange;font-weight:bold'>⏳ {row['Status']}</span>", unsafe_allow_html=True); st.divider()
                
                if tot_p > 1:
                    cp1, cp2, cp3 = st.columns([1, 2, 1])
                    if cp1.button("⬅️ ย้อนกลับ", disabled=st.session_state.page_pending==1, key="pp"): st.session_state.page_pending-=1; st.rerun()
                    cp2.markdown(f"<div style='text-align:center;'>{st.session_state.page_pending} / {tot_p}</div>", unsafe_allow_html=True)
                    if cp3.button("ถัดไป ➡️", disabled=st.session_state.page_pending==tot_p, key="pn"): st.session_state.page_pending+=1; st.rerun()

                st.markdown("<h4 style='color:#2e7d32; background-color:#e8f5e9; padding:10px; border-radius:5px;'>✅ รายการที่ดำเนินการเรียบร้อย</h4>", unsafe_allow_html=True)
                start_f, end_f, cur_f, tot_f = calculate_pagination('page_finished', len(df_f), 5)
                for i, row in df_f.iloc[start_f:end_f].iterrows():
                    cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                    with cc1: st.button(f"✅ {row['Report_ID']}", key=f"f_{i}", use_container_width=True, on_click=lambda r=row['Report_ID']: st.session_state.update({'selected_case_id': r, 'view_mode': 'detail', 'unlock_password': ""}))
                    cc2.write(row['Timestamp']); cc3.write(row['Incident_Type'])
                    cc4.markdown("<span style='color:green;font-weight:bold'>✅ เรียบร้อย</span>", unsafe_allow_html=True); st.divider()

            with tab_dash:
                tc = len(df_display)
                if tc > 0:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("แจ้งเหตุทั้งหมด", f"{tc} ครั้ง")
                    m2.metric("สถานที่เกิดเหตุบ่อยสุด", df_display['Location'].mode()[0] if not df_display.empty else "-")
                    m3.metric("เหตุที่เกิดบ่อยสุด", df_display['Incident_Type'].mode()[0] if not df_display.empty else "-")
                    st.markdown("---")
                    c_text1, c_text2 = st.columns(2)
                    with c_text1:
                        st.markdown("**📌 สรุปยอดตามสถานที่ (Top 5)**")
                        for l, c in df_display['Location'].value_counts().head(5).items():
                            p = (c/tc)*100; st.markdown(f"- **{l}**: {c} ครั้ง <span style='color:red; font-size:0.8em;'>({p:.1f}%)</span>", unsafe_allow_html=True)
                    with c_text2:
                        st.markdown("**📌 สรุปยอดตามประเภทเหตุ**")
                        for t, c in df_display['Incident_Type'].value_counts().head(5).items():
                            p = (c/tc)*100; st.markdown(f"- **{t}**: {c} ครั้ง <span style='color:red; font-size:0.8em;'>({p:.1f}%)</span>", unsafe_allow_html=True)
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1: st.markdown("**🔹 ประเภทเหตุ**"); st.bar_chart(df_display['Incident_Type'].value_counts(), color="#FF4B4B")
                    with col2: st.markdown("**🔹 สถานที่เกิดเหตุ**"); st.bar_chart(df_display['Location'].value_counts(), color="#1E3A8A")

        elif st.session_state.view_mode == "detail":
            st.button("⬅️ กลับหน้ารายการ", on_click=lambda: st.session_state.update({'view_mode': 'list'}), use_container_width=True)
            sid = st.session_state.selected_case_id
            sel = df_display[df_display['Report_ID'] == sid]
            if not sel.empty:
                idx_raw = sel.index[0]; row = sel.iloc[0]
                st.markdown(f"### 📝 เลขที่รับแจ้ง: {sid}")
                with st.container(border=True):
                    st.write(f"**ผู้แจ้ง:** {row['Reporter']} | **สถานที่:** {row['Location']}"); st.info(f"**รายละเอียด:** {row['Details']}")
                    if clean_val(row['Image_Data']): st.image(base64.b64decode(row['Image_Data']), width=500, caption="หลักฐานจากผู้แจ้ง")
                cur_sta = clean_val(row['Status'])
                is_lock = (cur_sta == "ดำเนินการเรียบร้อย" and st.session_state.unlock_password != "Patwit1510")
                if user.get('role') != 'admin': is_lock = True
                
                if is_lock and cur_sta == "ดำเนินการเรียบร้อย" and user.get('role') == 'admin':
                    pwd = st.text_input("รหัสปลดล็อค", type="password")
                    if st.button("ยืนยันปลดล็อค"):
                        if pwd == "Patwit1510": st.session_state.unlock_password = "Patwit1510"; st.rerun()

                with st.form("full_inv_form"):
                    c1, c2 = st.columns(2)
                    v_vic = c1.text_input("ผู้เสียหาย *", value=clean_val(row['Victim']), disabled=is_lock)
                    v_acc = c2.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row['Accused']), disabled=is_lock)
                    v_wit = c1.text_input("พยาน", value=clean_val(row['Witness']), disabled=is_lock)
                    v_tea = c2.text_input("ครูผู้สอบสวน *", value=clean_val(row['Teacher_Investigator']), disabled=is_lock)
                    v_stu = c1.text_input("ตำรวจนักเรียน *", value=clean_val(row['Student_Police_Investigator']), disabled=is_lock)
                    v_sta = c2.selectbox("สถานะ", ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"], index=["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"].index(cur_sta) if cur_sta in ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"] else 0, disabled=is_lock)
                    v_stmt = st.text_area("ผลการดำเนินการสอบสวน *", value=clean_val(row['Statement']), disabled=is_lock)
                    ev_img = st.file_uploader("📸 แนบรูปหลักฐานเพิ่ม", type=['jpg','png'], disabled=is_lock)
                    if st.form_submit_button("💾 บันทึกข้อมูล") and not is_lock:
                        df_raw.at[idx_raw, 'Victim'] = v_vic; df_raw.at[idx_raw, 'Accused'] = v_acc
                        df_raw.at[idx_raw, 'Witness'] = v_wit; df_raw.at[idx_raw, 'Teacher_Investigator'] = v_tea
                        df_raw.at[idx_raw, 'Student_Police_Investigator'] = v_stu
                        df_raw.at[idx_raw, 'Statement'] = v_stmt; df_raw.at[idx_raw, 'Status'] = v_sta
                        if ev_img: df_raw.at[idx_raw, 'Evidence_Image'] = process_image(ev_img)
                        df_raw.at[idx_raw, 'Audit_Log'] = f"{clean_val(row['Audit_Log'])}\n[{get_now_th().strftime('%d/%m/%Y %H:%M')}] แก้ไขโดย {user['name']}"
                        conn.update(data=df_raw.fillna("")); st.success("บันทึกเรียบร้อย!"); time.sleep(1); st.rerun()
                st.divider()
                try:
                    pdf_data = create_pdf_inv(row)
                    st.download_button(label="📥 ดาวน์โหลด PDF (สำนวนคดี)", data=pdf_data, file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True, type="primary")
                except: st.error("PDF ขัดข้อง")
    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 3. MODULE: TRAFFIC (CODE ของคุณ + Robust Universal Connection)
# ==========================================
def traffic_module():
    # Sync User Data
    st.session_state.officer_name = st.session_state.user_info.get('name', 'N/A')
    st.session_state.officer_role = st.session_state.user_info.get('role', 'teacher')
    
    st.sidebar.button("⬅️ กลับหน้าเลือกแผนก", on_click=lambda: setattr(st.session_state, 'current_dept', None), width='stretch')
    
    st.markdown("""
    <style>
        .metric-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .metric-value { font-size: 2.5rem; font-weight: 800; color: #1e293b; } .metric-percent { font-size: 1.1rem; color: #16a34a; font-weight: bold; }
        .atm-card { width: 100%; max-width: 450px; aspect-ratio: 1.586; background: white; border-radius: 15px; border: 2px solid #cbd5e1; padding: 20px; position: relative; color: #334155; margin: auto; }
        .atm-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; }
        .atm-logo { height: 55px; } .atm-photo { width: 100px; height: 125px; border-radius: 8px; object-fit: cover; border: 1px solid #cbd5e1; }
        .atm-score-box { position: absolute; bottom: 35px; right: 20px; text-align: right; } .atm-score-val { font-size: 32px; font-weight: 800; }
    </style>""", unsafe_allow_html=True)

    # --- UNIVERSAL CONNECTOR (หัวใจสำคัญของการแก้ปัญหา) ---
    def connect_gsheet_universal():
        # วิธีที่ 1: ดึงจาก connections.gsheets (ที่สอบสวนใช้ได้ชัวร์) แล้วแปลงเป็น Dict
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            creds_dict = dict(st.secrets["connections"]["gsheets"]) # แปลง AttrDict -> Dict
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds).open(SHEET_NAME_TRAFFIC).sheet1
        
        # วิธีที่ 2: ดึงจาก textkey (เผื่อมี)
        elif "textkey" in st.secrets:
            key_content = st.secrets["textkey"]["json_content"]
            key_dict = json.loads(key_content.replace('\n', '\\n'), strict=False)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
            return gspread.authorize(creds).open(SHEET_NAME_TRAFFIC).sheet1
        
        raise Exception("ไม่พบ Credentials ที่ถูกต้องใน secrets.toml")

    def load_data_tra():
        try:
            sheet = connect_gsheet_universal()
            vals = sheet.get_all_values()
            if len(vals) > 1:
                st.session_state.df_tra = pd.DataFrame(vals[1:], columns=[f"C{i}" for i, h in enumerate(vals[0])])
                return True
        except Exception as e: st.error(f"Error: {e}"); return False

    def upload_to_drive(file_obj, filename):
        file_content = file_obj.getvalue()
        base64_str = base64.b64encode(file_content).decode('utf-8')
        payload = {"folder_id": DRIVE_FOLDER_ID, "filename": filename, "file": base64_str, "mimeType": file_obj.type}
        try:
            res = requests.post(GAS_APP_URL, json=payload).json()
            return res.get("link") if res.get("status") == "success" else None
        except: return None

    def get_img_link(url):
        match = re.search(r'/d/([a-zA-Z0-9_-]+)|id=([a-zA-Z0-9_-]+)', str(url))
        file_id = match.group(1) or match.group(2) if match else None
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800" if file_id else url

    # --- ฟังก์ชัน PDF (จราจร - ต้นฉบับของคุณ) ---
    def create_pdf_tra(vals, img_url1, img_url2, face_url=None, printed_by="ระบบอัตโนมัติ"):
        buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=A4); width, height = A4
        if os.path.exists(FONT_FILE):
            pdfmetrics.registerFont(TTFont('Thai', FONT_FILE))
            pdfmetrics.registerFont(TTFont('ThaiBold', FONT_BOLD if os.path.exists(FONT_BOLD) else FONT_FILE))
            fn, fb = 'Thai', 'ThaiBold'
        else: fn, fb = 'Helvetica', 'Helvetica-Bold'
        logo = next((f for f in ["logo.png", "logo.jpg", "logo"] if os.path.exists(f)), None)
        if logo: c.drawImage(logo, 50, height - 85, width=50, height=50, mask='auto')
        c.setFont(fb, 22); c.drawCentredString(width/2, height - 50, "แบบทะเบียนประวัติรถจักรยานยนต์นักเรียน")
        c.setFont(fn, 18); c.drawCentredString(width/2, height - 72, "โรงเรียนโพนทองพัฒนาวิทยา")
        c.line(50, height - 85, width - 50, height - 85)
        # vals: C0=Time, C1=Name, C2=StdID, C3=Class, C4=Brand, C5=Color, C6=Plate, C7-9=Status, C10-11=ImgCar, C12=Log, C13=Score, C14=Face, C15=PIN
        name, std_id, classroom, brand, color, plate = str(vals[1]), str(vals[2]), str(vals[3]), str(vals[4]), str(vals[5]), str(vals[6])
        lic_s, tax_s, hel_s = str(vals[7]), str(vals[8]), str(vals[9])
        raw_note = str(vals[12]).strip() if len(vals) > 12 else ""
        note_text = raw_note if raw_note and raw_note.lower() != "nan" else "ไม่พบประวัติ"
        score = str(vals[13]) if len(vals) > 13 else "100"
        c.setFont(fn, 16); c.drawString(60, height - 115, f"ชื่อ-นามสกุล: {name}"); c.drawString(300, height - 115, f"ยี่ห้อรถ: {brand}")
        c.drawString(60, height - 135, f"รหัสนักเรียน: {std_id}"); c.drawString(300, height - 135, f"สีรถ: {color}")
        c.drawString(60, height - 155, f"ระดับชั้น: {classroom}"); c.setFont(fb, 16); c.drawString(300, height - 155, f"ทะเบียน: {plate}")
        c.setFont(fb, 18); c.drawString(60, height - 185, f"คะแนนความประพฤติจราจรคงเหลือ: {score} คะแนน")
        c.setFont(fn, 16); lm = "(/)" if "มี" in lic_s else "( )"; tm = "(/)" if "ปกติ" in tax_s else "( )"; hm = "(/)" if "มี" in hel_s else "( )"
        c.drawString(60, height - 210, f"สถานะเอกสาร:  {lm} ใบขับขี่    {tm} ภาษี/พรบ.    {hm} หมวกกันน็อค")
        def draw_img(url, x, y, w, h):
            try:
                if url:
                    res = requests.get(url, timeout=5); img_data = ImageReader(io.BytesIO(res.content))
                    c.drawImage(img_data, x, y, width=w, height=h, preserveAspectRatio=True, mask='auto'); c.rect(x, y, w, h)
            except: pass
        draw_img(img_url1, 70, height - 415, 180, 180); draw_img(img_url2, 300, height - 415, 180, 180)
        note_y = height - 455; c.setFont(fb, 16); c.drawString(60, note_y, "ประวัติบันทึกการทำผิดวินัยจราจร:")
        c.setFont(fn, 15); text_obj = c.beginText(70, note_y - 25); text_obj.setLeading(20)
        for line in note_text.split('\n'):
            for w_line in textwrap.wrap(line, width=75): text_obj.textLine(w_line)
        c.drawText(text_obj)
        sign_y = 180 
        c.setFont(fn, 16); c.drawString(60, sign_y, "ลงชื่อ ......................................... เจ้าของรถ"); c.drawString(100, sign_y - 20, f"({name})")
        if face_url: draw_img(face_url, 450, height - 200, 90, 110)
        c.drawString(320, sign_y, "ลงชื่อ ......................................... ครูผู้ตรวจสอบ"); c.drawString(340, sign_y - 20, "(.........................................)")
        c.setFont(fn, 10); c.setFillColorRGB(0.5, 0.5, 0.5)
        print_time = (datetime.now() + timedelta(hours=7)).strftime('%d/%m/%Y %H:%M')
        c.drawRightString(width - 30, 20, f"พิมพ์โดย: {printed_by} | เมื่อ: {print_time}")
        c.save(); buffer.seek(0); return buffer

    # Logic การทำงาน
    if st.session_state.df_tra is None:
        with st.spinner("⏳ กำลังโหลดข้อมูลจราจร..."): load_data_tra()

    if st.session_state.traffic_page == 'teacher':
        if 'df_tra' in st.session_state and st.session_state.df_tra is not None:
            df = st.session_state.df_tra
            col_u, col_l = st.columns([3, 1])
            col_u.info(f"👤 ผู้ใช้งาน: {st.session_state.officer_name}")
            with col_l:
                if st.button("🚪 ออกจากระบบ", key="tra_logout"): st.session_state.clear(); st.rerun()

            c1, c2 = st.columns(2)
            if c1.button("🔄 ดึงข้อมูลล่าสุด"): load_data_tra(); st.rerun()
            if c2.button("📊 รายงานสถิติ"): st.session_state.traffic_page = 'dash'; st.rerun()

            total = len(df); lok = df[df.iloc[:,7].str.contains("มี", na=False)].shape[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card"><div class="metric-value">{total}</div><div class="metric-label">รถทั้งหมด</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div class="metric-value">{lok}</div><div class="metric-label">มีใบขับขี่</div></div>', unsafe_allow_html=True)

            st.markdown("---")
            q = st.text_input("🔍 ค้นหา (ชื่อ/รหัส/ทะเบียน)")
            res_df = df[df.iloc[:, [1, 2, 6]].apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df.head(10)

            for i, row in res_df.iterrows():
                v = row.tolist()
                with st.expander(f"📍 {v[6]} | {v[1]}"):
                    st.markdown(f"### 👤 {v[1]} (รหัส: {v[2]})")
                    ci1, ci2, ci3 = st.columns(3)
                    ci1.image(get_img_link(v[14]), caption="เจ้าของรถ"); ci2.image(get_img_link(v[10]), caption="หลังรถ"); ci3.image(get_img_link(v[11]), caption="ข้างรถ")
                    
                    if st.session_state.officer_role == "admin":
                        with st.form(key=f"sc_{i}"):
                            pts = st.number_input("แต้ม", 1, 50, 5); note = st.text_area("เหตุผล"); pwd = st.text_input("รหัสยืนยัน", type="password")
                            if st.form_submit_button("🔴 หักแต้ม") and pwd == st.session_state.current_user_pwd:
                                sheet = connect_gsheet_universal(); cell = sheet.find(str(v[2]))
                                sc = int(v[13]) if len(v)>13 and str(v[13]).isdigit() else 100
                                ns = max(0, sc-pts)
                                # Log
                                tn = (datetime.now()+timedelta(hours=7)).strftime('%d/%m/%Y %H:%M')
                                old = str(v[12]).strip() if str(v[12]).lower()!="nan" else ""
                                new_log = f"{old}\n[{tn}] หัก {pts} คะแนน: {note} (โดย: {st.session_state.officer_name})"
                                sheet.update(f'M{cell.row}:N{cell.row}', [[new_log, str(ns)]])
                                st.success("บันทึกแล้ว"); load_data_tra(); st.rerun()
                        
                        st.download_button("📥 โหลด PDF", create_pdf_tra(v, get_img_link(v[10]), get_img_link(v[11]), get_img_link(v[14]), st.session_state.officer_name), f"{v[6]}.pdf")

    elif st.session_state.traffic_page == 'dash':
        if st.button("⬅️ กลับ"): st.session_state.traffic_page = 'teacher'; st.rerun()
        if 'df_tra' in st.session_state:
            st.plotly_chart(px.pie(st.session_state.df_tra, names='C7', title="ใบขับขี่"), use_container_width=True)

# ==========================================
# 4. MAIN ENTRY
# ==========================================
def main():
    if not st.session_state.logged_in:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h2 style='text-align:center;'>👮‍♂️ Central Login</h2>", unsafe_allow_html=True)
                pwd_in = st.text_input("รหัสผ่านเจ้าหน้าที่", type="password")
                if st.button("เข้าสู่ระบบ", width='stretch', type='primary'):
                    accs = st.secrets.get("OFFICER_ACCOUNTS", {})
                    if pwd_in in accs:
                        st.session_state.logged_in = True; st.session_state.user_info = accs[pwd_in]
                        st.session_state.current_user_pwd = pwd_in; st.rerun()
                    else: st.error("❌ รหัสผิด")
    else:
        if st.session_state.current_dept is None:
            st.title("🏢 เลือกแผนกปฏิบัติงาน")
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.subheader("🕵️ งานสอบสวน")
                    if st.button("เข้าใช้งานสอบสวน", use_container_width=True, type='primary'):
                        st.session_state.current_dept = "inv"; st.rerun()
            with c2:
                with st.container(border=True):
                    st.subheader("🚦 งานจราจร")
                    if st.button("เข้าใช้งานจราจร", use_container_width=True, type='primary'):
                        st.session_state.current_dept = "tra"; st.session_state.traffic_page = 'teacher'; st.rerun()
        else:
            if st.session_state.current_dept == "inv": investigation_module()
            elif st.session_state.current_dept == "tra": traffic_module()

if __name__ == "__main__": main()
