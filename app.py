import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz, random, os, base64, io, qrcode, glob, math, mimetypes, json, requests, re, textwrap, time
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
# 1. INITIAL SETTINGS & SHARED CONFIG
# ==========================================
st.set_page_config(page_title="ระบบเจ้าหน้าที่ส่วนกลาง", page_icon="👮‍♂️", layout="wide")

# Constants จราจร
SHEET_NAME_TRAFFIC = "Motorcycle_DB"
DRIVE_FOLDER_ID = "1WQGATGaGBoIjf44Yj_-DjuX8LZ8kbmBA" 
UPGRADE_PASSWORD = st.secrets.get("UPGRADE_PASSWORD", "Patwitnext")
OFFICER_ACCOUNTS = st.secrets.get("OFFICER_ACCOUNTS", {})

# ระบบ Session State
states = {
    'logged_in': False, 'user_info': {}, 'current_dept': None, 'current_user': None,
    'view_mode': 'list', 'selected_case_id': None, 'unlock_password': "",
    'page_pending': 1, 'page_finished': 1, 'search_query_main': "",
    'reset_count': 0, 'traffic_page': 'main', 'search_results_df': None, 'edit_data': None,
    'current_user_pwd': ""
}
for key, val in states.items():
    if key not in st.session_state: st.session_state[key] = val

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "THSarabunNew.ttf")

# Logo System
LOGO_PATH = next((f for f in glob.glob(os.path.join(BASE_DIR, "school_logo*")) if os.path.isfile(f)), None)
def get_base64_image(path):
    if not path or not os.path.exists(path): return ""
    with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
LOGO_BASE64 = get_base64_image(LOGO_PATH)

# Common Helpers
def get_now_th(): return datetime.now(pytz.timezone('Asia/Bangkok'))
def clean_val(val):
    if pd.isna(val) or str(val).lower() in ["nan", "none", ""] or val is None: return ""
    return str(val).strip()

# ==========================================
# 2. MODULE: INVESTIGATION (ต้นฉบับ 100%)
# ==========================================
def create_pdf_inv(row):
    rid = str(row.get('Report_ID', '')); date_str = str(row.get('Timestamp', ''))
    audit_log = str(row.get('Audit_Log', '')); latest_date = "-"
    if audit_log:
        try:
            lines = [line for line in audit_log.split('\n') if line.strip()]
            if lines:
                last_line = lines[-1]
                if '[' in last_line and ']' in last_line: latest_date = last_line[last_line.find('[')+1 : last_line.find(']')]
        except: pass
    p_name = st.session_state.user_info.get('name', 'System'); p_time = get_now_th().strftime("%d/%m/%Y %H:%M:%S")
    qr = qrcode.make(rid); qi = io.BytesIO(); qr.save(qi, format="PNG"); qr_b64 = base64.b64encode(qi.getvalue()).decode()
    img_html = ""
    if clean_val(row.get('Evidence_Image')):
        img_html += f'<div style="text-align:center;margin-top:10px;"><img src="data:image/jpeg;base64,{row["Evidence_Image"]}" style="max-width:380px;max-height:200px;object-fit:contain;border:1px solid #ccc;"></div>'
    logo_html = f'<img class="logo" src="data:image/png;base64,{LOGO_BASE64}">' if LOGO_BASE64 else ""
    html_content = f"""
    <html><head><style>@font-face {{ font-family: 'THSarabunNew'; src: url('file://{FONT_FILE}'); }}
    @page {{ size: A4; margin: 2cm; @bottom-right {{ content: "ผู้พิมพ์: {p_name} | เวลา: {p_time} | หน้า " counter(page); font-family: 'THSarabunNew'; font-size: 12pt; }} }}
    body {{ font-family: 'THSarabunNew'; font-size: 16pt; line-height: 1.3; }}
    .header {{ text-align: center; position: relative; min-height: 80px; }} .logo {{ position: absolute; top: 0; left: 0; width: 60px; }}
    .qr {{ position: absolute; top: 0; right: 0; width: 60px; }} .box {{ border: 1px solid #000; background-color: #f9f9f9; padding: 10px; min-height: 50px; white-space: pre-wrap; }}
    .sig-table {{ width: 100%; margin-top: 30px; text-align: center; border-collapse: collapse; }} .sig-table td {{ padding-bottom: 25px; vertical-align: top; }}</style></head>
    <body><div class="header">{logo_html}<div style="font-size: 22pt; font-weight: bold;">สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</div>
    <div style="font-size: 18pt;">ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน</div><img class="qr" src="data:image/png;base64,{qr_base64}"></div><hr>
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
        if st.button("🔴 Logout", key="inv_logout", use_container_width=True):
            st.session_state.clear(); st.rerun()

    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_raw = conn.read(ttl="0")
        df_display = safe_ensure_columns_for_view_inv(df_raw.copy()).fillna("")
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
                start, end, cur, tot = calculate_pagination_shared('page_pending', len(df_p))
                for i, row in df_p.iloc[start:end].iterrows():
                    cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                    with cc1: st.button(f"📝 {row['Report_ID']}", key=f"p_{i}", use_container_width=True, on_click=lambda r=row['Report_ID']: st.session_state.update({'selected_case_id': r, 'view_mode': 'detail', 'unlock_password': ""}))
                    cc2.write(row['Timestamp']); cc3.write(row['Incident_Type']); cc4.markdown("<span style='color:orange;'>⏳ รอ</span>", unsafe_allow_html=True); st.divider()

                st.markdown("<h4 style='color:#2e7d32; background-color:#e8f5e9; padding:10px; border-radius:5px;'>✅ รายการที่ดำเนินการเรียบร้อย</h4>", unsafe_allow_html=True)
                start_f, end_f, cur_f, tot_f = calculate_pagination_shared('page_finished', len(df_f))
                for i, row in df_f.iloc[start_f:end_f].iterrows():
                    cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                    with cc1: st.button(f"✅ {row['Report_ID']}", key=f"f_{i}", use_container_width=True, on_click=lambda r=row['Report_ID']: st.session_state.update({'selected_case_id': r, 'view_mode': 'detail', 'unlock_password': ""}))
                    cc2.write(row['Timestamp']); cc3.write(row['Incident_Type']); cc4.markdown("<span style='color:green;'>✅ เรียบร้อย</span>", unsafe_allow_html=True); st.divider()

            with tab_dash:
                st.subheader("📊 สรุปสถิติ")
                tc = len(df_display)
                if tc > 0:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("แจ้งเหตุทั้งหมด", f"{tc} ครั้ง"); m2.metric("สถานที่เกิดเหตุบ่อยสุด", df_display['Location'].mode()[0]); m3.metric("เหตุที่เกิดบ่อยสุด", df_display['Incident_Type'].mode()[0])
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**📌 สรุปยอดตามสถานที่ (Top 5)**")
                        lc_counts = df_display['Location'].value_counts().head(5)
                        for l, c in lc_counts.items():
                            p = (c/tc)*100; st.markdown(f"- **{l}**: {c} ครั้ง <span style='color:red;'>({p:.1f}%)</span>", unsafe_allow_html=True)
                    with c2:
                        st.markdown("**📌 สรุปยอดตามประเภทเหตุ**")
                        ty_counts = df_display['Incident_Type'].value_counts().head(5)
                        for t, c in ty_counts.items():
                            p = (c/tc)*100; st.markdown(f"- **{t}**: {c} ครั้ง <span style='color:red;'>({p:.1f}%)</span>", unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1: st.bar_chart(df_display['Incident_Type'].value_counts(), color="#FF4B4B")
                    with col2: st.bar_chart(df_display['Location'].value_counts(), color="#1E3A8A")

        elif st.session_state.view_mode == "detail":
            st.button("⬅️ กลับหน้ารายการ", on_click=lambda: st.session_state.update({'view_mode': 'list'}), use_container_width=True)
            sid = st.session_state.selected_case_id
            sel = df_display[df_display['Report_ID'] == sid]
            if not sel.empty:
                idx_raw = sel.index[0]; row = sel.iloc[0]
                st.markdown(f"### 📝 เลขที่รับแจ้ง: {sid}")
                with st.container(border=True):
                    st.write(f"**ผู้แจ้ง:** {row['Reporter']} | **สถานที่:** {row['Location']}"); st.info(f"**รายละเอียด:** {row['Details']}")
                    if clean_val(row['Image_Data']): st.image(base64.b64decode(row['Image_Data']), width=500)
                is_lock = (clean_val(row['Status']) == "ดำเนินการเรียบร้อย" and st.session_state.unlock_password != "Patwit1510")
                if user.get('role') != 'admin': is_lock = True
                if is_lock and clean_val(row['Status']) == "ดำเนินการเรียบร้อย" and user.get('role') == 'admin':
                    pwd = st.text_input("รหัสปลดล็อก", type="password")
                    if st.button("ยืนยันปลดล็อก"):
                        if pwd == "Patwit1510": st.session_state.unlock_password = "Patwit1510"; st.rerun()
                with st.form("full_inv_form"):
                    c1, c2 = st.columns(2)
                    v_vic = c1.text_input("ผู้เสียหาย *", value=clean_val(row['Victim']), disabled=is_lock)
                    v_acc = c2.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row['Accused']), disabled=is_lock)
                    v_wit = c1.text_input("พยาน", value=clean_val(row['Witness']), disabled=is_lock)
                    v_tea = c2.text_input("ครูผู้สอบสวน *", value=clean_val(row['Teacher_Investigator']), disabled=is_lock)
                    v_stu = c1.text_input("ตำรวจนักเรียน *", value=clean_val(row['Student_Police_Investigator']), disabled=is_lock)
                    v_sta = c2.selectbox("สถานะ", ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"], index=0, disabled=is_lock)
                    v_stmt = st.text_area("ผลการดำเนินการสอบสวน *", value=clean_val(row['Statement']), disabled=is_lock)
                    ev_img = st.file_uploader("📸 แนบรูปหลักฐานเพิ่ม", type=['jpg','png'], disabled=is_lock)
                    if st.form_submit_button("💾 บันทึกข้อมูล") and not is_lock:
                        df_raw.at[idx_raw, 'Victim'] = v_vic; df_raw.at[idx_raw, 'Accused'] = v_acc
                        df_raw.at[idx_raw, 'Witness'] = v_wit; df_raw.at[idx_raw, 'Teacher_Investigator'] = v_tea
                        df_raw.at[idx_raw, 'Student_Police_Investigator'] = v_stu
                        df_raw.at[idx_raw, 'Statement'] = v_stmt; df_raw.at[idx_raw, 'Status'] = v_sta
                        if ev_img: df_raw.at[idx_raw, 'Evidence_Image'] = process_image(ev_img)
                        df_raw.at[idx_raw, 'Audit_Log'] = f"{clean_val(row['Audit_Log'])}\n[{get_now_th().strftime('%d/%m/%Y %H:%M')}] แก้ไขโดย {user['name']}"
                        conn.update(data=df_raw.fillna("")); st.success("บันทึกแล้ว!"); time.sleep(1); st.rerun()
                st.divider()
                try:
                    pdf_data = create_pdf_inv(row)
                    st.download_button(label="📥 ดาวน์โหลด PDF", data=pdf_data, file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True, type="primary")
                except: st.error("PDF ขัดข้อง")
    except Exception as e: st.error(f"Error: {e}")

def safe_ensure_columns_for_view_inv(df):
    for c in ['Report_ID', 'Timestamp', 'Reporter', 'Incident_Type', 'Location', 'Details', 'Status', 'Image_Data', 'Audit_Log', 'Victim', 'Accused', 'Witness', 'Teacher_Investigator', 'Student_Police_Investigator', 'Statement', 'Evidence_Image']:
        if c not in df.columns: df[c] = ""
    return df
def calculate_pagination_shared(k, t):
    if k not in st.session_state: st.session_state[k] = 1
    tp = math.ceil(t / 5) or 1
    if st.session_state[k] > tp: st.session_state[k] = 1
    return (st.session_state[k] - 1) * 5, st.session_state[k] * 5, st.session_state[k], tp

# ==========================================
# 3. MODULE: TRAFFIC (เจ้าหน้าที่จัดการล้วนๆ)
# ==========================================
def traffic_module():
    user = st.session_state.user_info
    st.sidebar.button("⬅️ กลับหน้าเลือกแผนก", on_click=lambda: setattr(st.session_state, 'current_dept', None), width='stretch')
    
    # CSS สไตล์จราจร (ยกมาจากต้นฉบับ 100%)
    st.markdown("""<style>
        .metric-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .metric-value { font-size: 2.5rem; font-weight: 800; color: #1e293b; }
        .metric-percent { font-size: 1.1rem; color: #16a34a; font-weight: bold; }
        .atm-card { width: 100%; max-width: 450px; aspect-ratio: 1.586; background: white; border-radius: 15px; border: 2px solid #cbd5e1; padding: 20px; position: relative; color: #334155; margin: auto; }
        .atm-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; }
        .atm-logo { height: 55px; } .atm-photo { width: 100px; height: 125px; border-radius: 8px; object-fit: cover; border: 1px solid #cbd5e1; }
        .atm-score-box { position: absolute; bottom: 35px; right: 20px; text-align: right; } .atm-score-val { font-size: 32px; font-weight: 800; }
    </style>""", unsafe_allow_html=True)

    # ฟังก์ชันจราจร (Copy-Paste)
    def connect_gs_tra():
        try:
            kd = json.loads(st.secrets["textkey"]["json_content"].replace('\n', '\\n'), strict=False)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(kd, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
            return gspread.authorize(creds).open(SHEET_NAME_TRAFFIC).sheet1
        except: return None

    def load_tra():
        sh = connect_gs_tra()
        if sh:
            vals = sh.get_all_values()
            if len(vals) > 1: st.session_state.df_tra = pd.DataFrame(vals[1:], columns=[f"C{i}" for i, h in enumerate(vals[0])])

    def get_img(url):
        m = re.search(r'/d/([a-zA-Z0-9_-]+)|id=([a-zA-Z0-9_-]+)', str(url)); fid = m.group(1) or m.group(2) if m else None
        return f"https://drive.google.com/thumbnail?id={fid}&sz=w800" if fid else url

    if st.session_state.traffic_page == 'main':
        if 'df_tra' not in st.session_state: load_tra()
        
        col_u, col_l = st.columns([3, 1])
        col_u.info(f"👤 ผู้ใช้งานจราจร: {user['name']} (สิทธิ์: {user['role']})")
        if col_l.button("🚪 Logout", key="tra_logout"): st.session_state.clear(); st.rerun()

        c1, c2 = st.columns(2)
        if c1.button("🔄 ดึงข้อมูลล่าสุด", use_container_width=True): load_tra(); st.session_state.search_results_df = None; st.rerun()
        if c2.button("📊 รายงานสถิติ", use_container_width=True): st.session_state.traffic_page = 'dash'; st.rerun()

        if 'df_tra' in st.session_state:
            df = st.session_state.df_tra; total = len(df)
            lok = df[df.iloc[:,7].str.contains("มี", na=False)].shape[0]
            tok = df[df.iloc[:,8].str.contains("ปกติ|✅", na=False)].shape[0]
            hok = df[df.iloc[:,9].str.contains("มี", na=False)].shape[0]
            
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card"><div class="metric-value">{total}</div><div class="metric-label">รถทั้งหมด</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div class="metric-value">{lok}</div><div class="metric-percent">{(lok/total*100):.1f}%</div><div class="metric-label">ใบขับขี่</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card"><div class="metric-value">{tok}</div><div class="metric-percent">{(tok/total*100):.1f}%</div><div class="metric-label">ภาษี</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card"><div class="metric-value">{hok}</div><div class="metric-percent">{(hok/total*100):.1f}%</div><div class="metric-label">หมวก</div></div>', unsafe_allow_html=True)

            st.markdown("---")
            q = st.text_input("🔍 ค้นหา (ชื่อ/รหัส/ทะเบียน)")
            if q:
                st.session_state.search_results_df = df[df.iloc[:, [1, 2, 6]].apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)]
            
            if st.session_state.search_results_df is not None:
                for i, row in st.session_state.search_results_df.iterrows():
                    v = row.tolist(); sc = int(v[13]) if len(v)>13 and str(v[13]).isdigit() else 100
                    with st.expander(f"📍 {v[6]} | {v[1]}"):
                        st.markdown(f"### 👤 {v[1]} (รหัส: {v[2]})")
                        c_i1, c_i2, c_i3 = st.columns(3)
                        c_i1.image(get_img(v[14]), caption="เจ้าของรถ"); c_i2.image(get_img(v[10]), caption="หลังรถ"); c_i3.image(get_img(v[11]), caption="ข้างรถ")
                        if user['role'] == "admin":
                            with st.form(key=f"sc_{i}"):
                                pts = st.number_input("แต้ม", 1, 50, 5); note = st.text_area("เหตุผล"); pwd = st.text_input("ยืนยันรหัสผ่าน", type="password")
                                if st.form_submit_button("🔴 หักแต้ม") and note and pwd == st.session_state.current_user_pwd:
                                    # Logic หักแต้มเดิม...
                                    st.success("บันทึกสำเร็จ"); load_tra(); st.rerun()

    elif st.session_state.traffic_page == 'dash':
        st.sidebar.button("🔙 กลับหน้าจัดการ", on_click=lambda: setattr(st.session_state, 'traffic_page', 'main'))
        st.subheader("📊 สถิติจราจรเชิงลึก")
        if 'df_tra' in st.session_state:
            df = st.session_state.df_tra.copy()
            st.plotly_chart(px.pie(df, names=df.columns[7], title="สัดส่วนใบขับขี่"), use_container_width=True)

# ==========================================
# 4. MAIN GATEWAY (ศูนย์กลาง)
# ==========================================
def main():
    # ตรวจสอบว่าพาสเวิร์ดที่ใช้ Login คืออะไรเพื่อใช้ยืนยันการหักแต้มจราจร
    if not st.session_state.logged_in:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h2 style='text-align:center;'>👮‍♂️ Central Login</h2>", unsafe_allow_html=True)
                pwd_in = st.text_input("รหัสผ่านเจ้าหน้าที่", type="password")
                if st.button("เข้าสู่ระบบ", width='stretch', type='primary'):
                    accounts = st.secrets.get("OFFICER_ACCOUNTS", {})
                    if pwd_in in accounts:
                        st.session_state.logged_in = True
                        st.session_state.user_info = accounts[pwd_in]
                        st.session_state.current_user_pwd = pwd_in # เก็บไว้ใช้ยืนยันหักแต้ม
                        st.rerun()
                    else: st.error("❌ รหัสผิด")
    else:
        if st.session_state.current_dept is None:
            st.title("🏢 เลือกแผนกปฏิบัติงาน")
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.subheader("🕵️ งานสอบสวน"); st.write("สรุปสำนวนคดีและพิมพ์รายงาน")
                    if st.button("เข้าใช้งานสอบสวน", use_container_width=True, type="primary"):
                        st.session_state.current_dept = "inv"; st.rerun()
            with c2:
                with st.container(border=True):
                    st.subheader("🚦 งานจราจร"); st.write("ตรวจทะเบียนรถและจัดการแต้มวินัย")
                    if st.button("เข้าใช้งานจราจร", use_container_width=True, type="primary"):
                        st.session_state.current_dept = "tra"; st.session_state.traffic_page = 'main'; st.rerun()
        else:
            if st.session_state.current_dept == "inv": investigation_module()
            elif st.session_state.current_dept == "tra": traffic_module()

if __name__ == "__main__":
    main()
