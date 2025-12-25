import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json
import requests
import base64
import time
import io
import re
import os
import textwrap
import plotly.express as px

# --- ส่วนของ PDF Library ---
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- 1. ตั้งค่า (Config) ---
SHEET_NAME = "Motorcycle_DB"
DRIVE_FOLDER_ID = "1WQGATGaGBoIjf44Yj_-DjuX8LZ8kbmBA" 
# ดึงรหัสผ่านและบัญชีจาก Streamlit Secrets
UPGRADE_PASSWORD = st.secrets["UPGRADE_PASSWORD"] 
OFFICER_ACCOUNTS = st.secrets["OFFICER_ACCOUNTS"]

GAS_APP_URL = "https://script.google.com/macros/s/AKfycbxRf6z032SxMkiI4IxtUBvWLKeo1LmIQAUMByoXidy4crNEwHoO6h0B-3hT0X7Q5g/exec" 
SESSION_TIMEOUT_MINUTES = 30 

# --- 2. Setup หน้าเว็บ ---
st.set_page_config(page_title="patwit moto.", page_icon="logo", layout="wide")

# --- 3. ฟังก์ชันระบบ ---
if 'reset_count' not in st.session_state: st.session_state['reset_count'] = 0
if 'page' not in st.session_state: st.session_state['page'] = 'student'
if 'search_results_df' not in st.session_state: st.session_state['search_results_df'] = None
if 'edit_data' not in st.session_state: st.session_state['edit_data'] = None
if 'officer_name' not in st.session_state: st.session_state['officer_name'] = "" 
if 'officer_role' not in st.session_state: st.session_state['officer_role'] = ""
if 'current_user_pwd' not in st.session_state: st.session_state['current_user_pwd'] = ""
if 'last_active' not in st.session_state: st.session_state['last_active'] = time.time()

def check_session_timeout():
    if st.session_state.get('logged_in'):
        current_time = time.time()
        if current_time - st.session_state['last_active'] > (SESSION_TIMEOUT_MINUTES * 60):
            logout()
            st.warning(f"⏳ หมดเวลาการเชื่อมต่อ (เกิน {SESSION_TIMEOUT_MINUTES} นาที) กรุณาเข้าสู่ระบบใหม่")
            st.stop()
        else:
            st.session_state['last_active'] = current_time

def logout():
    st.session_state.logged_in = False
    st.session_state.officer_name = ""
    st.session_state.officer_role = ""
    st.session_state.current_user_pwd = ""
    st.session_state.page = "teacher"
    st.rerun()

def img_to_b64(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def connect_gsheet():
    key_content = st.secrets["textkey"]["json_content"]
    try: key_dict = json.loads(key_content, strict=False)
    except: key_dict = json.loads(key_content.replace('\n', '\\n'), strict=False)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def load_data():
    try:
        sheet = connect_gsheet()
        vals = sheet.get_all_values()
        if len(vals) > 1:
            st.session_state.df = pd.DataFrame(vals[1:], columns=[f"C{i}" for i, h in enumerate(vals[0])])
            return True
    except Exception as e:
        st.error(f"โหลดข้อมูลไม่สำเร็จ: {e}")
        return False
    return False

def clear_form_state():
    keys_to_clear = ["reg_fname", "reg_id", "reg_room", "reg_pin", "reg_brand", "reg_color", "reg_plate"]
    for key in keys_to_clear:
        if key in st.session_state:
            st.session_state[key] = ""

def reset_results(): st.session_state['search_results_df'] = None
def go_to_page(page_name): st.session_state['page'] = page_name; st.rerun()

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

# --- ฟังก์ชัน PDF ---
def create_pdf(vals, img_url1, img_url2, face_url=None, printed_by="ระบบอัตโนมัติ"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    f_reg, f_bold = "THSarabunNew.ttf", "THSarabunNewBold.ttf"
    font_name, font_bold = ('Thai', 'ThaiBold') if os.path.exists(f_reg) else ('Helvetica', 'Helvetica-Bold')
    if font_name == 'Thai':
        pdfmetrics.registerFont(TTFont('Thai', f_reg))
        pdfmetrics.registerFont(TTFont('ThaiBold', f_bold))
    logo = next((f for f in ["logo.png", "logo.jpg", "logo"] if os.path.exists(f)), None)
    if logo: c.drawImage(logo, 50, height - 85, width=50, height=50, mask='auto')
    
    c.setFont(font_bold, 22); c.drawCentredString(width/2, height - 50, "แบบทะเบียนประวัติรถจักรยานยนต์นักเรียน")
    c.setFont(font_name, 18); c.drawCentredString(width/2, height - 72, "โรงเรียนโพนทองพัฒนาวิทยา")
    c.line(50, height - 85, width - 50, height - 85)
    
    name, std_id, classroom, brand, color, plate = str(vals[1]), str(vals[2]), str(vals[3]), str(vals[4]), str(vals[5]), str(vals[6])
    lic_s, tax_s, hel_s = str(vals[7]), str(vals[8]), str(vals[9])
    raw_note = str(vals[12]).strip() if len(vals) > 12 else ""
    note_text = raw_note if raw_note and raw_note.lower() != "nan" else "ไม่พบประวัติ"
    score = str(vals[13]) if len(vals) > 13 and str(vals[13]).lower() != "nan" else "100"
    
    c.setFont(font_name, 16)
    c.drawString(60, height - 115, f"ชื่อ-นามสกุล: {name}"); c.drawString(300, height - 115, f"ยี่ห้อรถ: {brand}")
    c.drawString(60, height - 135, f"รหัสนักเรียน: {std_id}"); c.drawString(300, height - 135, f"สีรถ: {color}")
    c.drawString(60, height - 155, f"ระดับชั้น: {classroom}"); c.setFont(font_bold, 16); c.drawString(300, height - 155, f"ทะเบียน: {plate}")
    
    c.setFont(font_bold, 18); color_val = (0.7, 0, 0) if int(score) < 80 else (0, 0.5, 0); c.setFillColorRGB(*color_val)
    c.drawString(60, height - 185, f"คะแนนความประพฤติจราจรคงเหลือ: {score} คะแนน"); c.setFillColorRGB(0, 0, 0)
    c.setFont(font_name, 16); lm = "(/)" if "มี" in lic_s else "( )"; tm = "(/)" if "ปกติ" in tax_s or "✅" in tax_s else "( )"; hm = "(/)" if "มี" in hel_s else "( )"
    c.drawString(60, height - 210, f"สถานะเอกสาร:  {lm} ใบขับขี่    {tm} ภาษี/พรบ.    {hm} หมวกกันน็อค")
    
    def draw_img_func(url, x, y, w, h):
        try:
            if url and "drive.google.com" in url:
                res = requests.get(url, timeout=5)
                img_data = ImageReader(io.BytesIO(res.content))
                c.drawImage(img_data, x, y, width=w, height=h, preserveAspectRatio=True, mask='auto')
                c.rect(x, y, w, h)
        except: pass

    draw_img_func(img_url1, 70, height - 415, 180, 180)
    draw_img_func(img_url2, 300, height - 415, 180, 180)

    note_y = height - 455; c.setFont(font_bold, 16); c.drawString(60, note_y, "ประวัติบันทึกการทำผิดวินัยจราจร:")
    c.setFont(font_name, 15); text_obj = c.beginText(70, note_y - 25); text_obj.setLeading(20)
    for line in note_text.split('\n'):
        for w_line in textwrap.wrap(line, width=75): text_obj.textLine(w_line)
    c.drawText(text_obj)
    
    sign_y = 180 
    c.setFont(font_name, 16)
    c.drawString(60, sign_y, "ลงชื่อ ......................................... เจ้าของรถ")
    c.drawString(100, sign_y - 20, f"({name})")

    if face_url:
        draw_img_func(face_url, 450, height - 200, 90, 110)

    c.drawString(320, sign_y, "ลงชื่อ ......................................... ครูผู้ตรวจสอบ")
    c.drawString(340, sign_y - 20, "(.........................................)")
    
    c.setFont(font_name, 10)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    print_time = (datetime.now() + timedelta(hours=7)).strftime('%d/%m/%Y %H:%M')
    c.drawRightString(width - 30, 20, f"พิมพ์โดย: {printed_by} | เมื่อ: {print_time}")
    
    c.save(); buffer.seek(0); return buffer

st.markdown("""
    <style>
        header { visibility: hidden !important; height: 0px !important; }
        footer { visibility: hidden !important; height: 0px !important; }
        [data-testid="stSidebar"] { display: none; }
        .block-container { padding-top: 2rem; }
        .metric-card {
            background-color: #ffffff; padding: 15px; border-radius: 10px;
            border: 1px solid #e2e8f0; text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .metric-value { font-size: 2.5rem; font-weight: 800; color: #1e293b; line-height: 1.2; }
        .metric-percent { font-size: 1.1rem; color: #16a34a; font-weight: bold; margin-top: -5px; margin-bottom: 5px; }
        .metric-label { font-size: 1rem; color: #64748b; }
        .score-display {
            font-size: 1.5rem; font-weight: bold; color: #ef4444;
            background: #fee2e2; padding: 10px; border-radius: 8px; text-align: center;
            margin-bottom: 10px;
        }
        .atm-card {
            width: 100%; max-width: 450px; aspect-ratio: 1.586;
            background: #ffffff; border-radius: 15px; border: 2px solid #cbd5e1;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 20px; position: relative; font-family: 'Sarabun', sans-serif;
            color: #334155; margin: auto;
        }
        .atm-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; }
        .atm-logo { height: 55px; width: auto; }
        .atm-title { text-align: right; }
        .atm-school-name { font-size: 16px; font-weight: bold; color: #1e293b; }
        .atm-card-name { font-size: 14px; color: #059669; font-weight: bold; }
        .atm-body { display: flex; gap: 15px; }
        .atm-photo { width: 100px; height: 125px; border-radius: 8px; object-fit: cover; border: 1px solid #cbd5e1; background-color: #f1f5f9; }
        .atm-info { font-size: 14px; line-height: 1.5; flex: 1; color: #334155; }
        .atm-score-box { position: absolute; bottom: 35px; right: 20px; text-align: right; }
        .atm-score-label { font-size: 12px; color: #64748b; }
        .atm-score-val { font-size: 32px; font-weight: 800; line-height: 1; }
        .atm-disclaimer { position: absolute; bottom: 8px; right: 15px; font-size: 9px; color: #ef4444; opacity: 0.8; font-style: italic; }
        
        div[data-testid="stForm"] { border: 1px solid #e2e8f0; padding: 20px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 4. Main UI ---
check_session_timeout()

c_logo, c_title = st.columns([1, 8])
logo_path = next((f for f in ["logo.png", "logo.jpg", "logo"] if os.path.exists(f)), None)
with c_logo:
    if logo_path: st.image(logo_path, width=90)
    else: st.write("🏍️")
with c_title: st.title("ระบบลงทะเบียนรถจักรยานยนต์โรงเรียนโพนทองพัฒนาวิทยา")
st.markdown("---")

if st.session_state.get('logged_in'):
    with st.sidebar:
        st.write(f"👤 **{st.session_state.officer_name}**")
        st.caption(f"สถานะ: {st.session_state.officer_role}")
        if st.button("🚪 ออกจากระบบ", type="secondary", use_container_width=True):
            logout()

if st.session_state['page'] == 'student':
    if st.session_state.get("reg_success", False):
        st.success("✅ ลงทะเบียนสำเร็จ! กรุณาจำรหัส PIN เพื่อใช้โหลดบัตร")
        st.balloons()
        clear_form_state()
        st.session_state.reg_success = False

    st.info("📝 ลงทะเบียนรถและทำบัตรอนุญาตดิจิทัล")
    with st.form("reg_form", clear_on_submit=False):
        sc1, sc2 = st.columns(2)
        with sc1:
            prefix = st.selectbox("คำนำหน้า", ["นาย", "นางสาว", "เด็กชาย", "เด็กหญิง", "นาง", "ครู"])
            fname = st.text_input("ชื่อ-นามสกุล", key="reg_fname")
        std_id = sc2.text_input("รหัสนักเรียน/ กรณีครูบุคลากรพ่อค้าแม่ค้า ระบุวันเดือนปีเกิด เช่น 02092530", key="reg_id")
        sc3, sc4 = st.columns(2)
        level = st.selectbox("ชั้น", ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6", "ครู,บุคลากร", "พ่อค้าแม่ค้า"])
        room = st.text_input("ห้อง(0-13) กรณีไม่ใช่นักเรียนกรอก 0", key="reg_room")
        st.write("🔐 **ตั้งค่าความปลอดภัย**")
        pin = st.text_input("ตั้งรหัส PIN 6 หลัก (สำหรับโหลดบัตรอนุญาต)", type="password", max_chars=6, key="reg_pin", help="ห้ามใช้เลขซ้ำกันทั้งหมด")
        sc5, sc6 = st.columns(2)
        brand = st.selectbox("ยี่ห้อ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"], key="reg_brand")
        color = st.text_input("สีรถ", key="reg_color")
        plate = st.text_input("ทะเบียนรถ", placeholder="เช่น 1กข 1234ร้อยเอ็ด", key="reg_plate")
        doc_cols = st.columns(3)
        ls = doc_cols[0].radio("ใบขับขี่", ["✅ มี", "❌ ไม่มี"], horizontal=True)
        ts = doc_cols[1].radio("ภาษี/พรบ", ["✅ ปกติ", "❌ ขาด"], horizontal=True)
        hs = doc_cols[2].radio("หมวกกันน็อค", ["✅ มี", "❌ ไม่มี"], horizontal=True)
        st.write("📸 **อัปโหลดภาพ (จำเป็น)**")
        up1, up2, up3 = st.columns(3)
        p_face = up1.file_uploader("1. รูปเจ้าของรถ", type=['jpg','png','jpeg'])
        p_back = up2.file_uploader("2. รูปด้านหลังรถจักรยานยนต์(เห็นป้าย)", type=['jpg','png','jpeg'])
        p_side = up3.file_uploader("3. รูปด้านข้างรถจักรยานยนต์(เห็นเต็มคัน)", type=['jpg','png','jpeg'])
        pdpa = st.checkbox("ข้าพเจ้ายินยอมให้โรงเรียนเก็บข้อมูลและรูปภาพเพื่อใช้ในระบบรักษาความปลอดภัยจราจร")

        if st.form_submit_button("ส่งข้อมูลลงทะเบียน", type="primary", use_container_width=True):
            errors = []
            if not fname: errors.append("ชื่อ-นามสกุล")
            if not std_id: errors.append("รหัสประจำตัว")
            if not plate: errors.append("ทะเบียนรถ")
            if not p_face: errors.append("รูปถ่ายหน้าตรง")
            if not p_back: errors.append("รูปถ่ายหลังรถ")
            if not pin or len(pin) != 6 or not pin.isdigit(): errors.append("รหัส PIN ต้องเป็นตัวเลข 6 หลัก")
            elif len(set(pin)) == 1: errors.append("รหัส PIN ห้ามใช้เลขซ้ำกันทั้งหมด")
            if not pdpa: errors.append("การยอมรับเงื่อนไข (PDPA)")

            if errors:
                st.error(f"❌ กรุณากรอกข้อมูลให้ครบถ้วน: {', '.join(errors)}")
            else:
                try:
                    sheet = connect_gsheet()
                    if str(std_id) in sheet.col_values(3): st.error("❌ รหัสนี้เคยลงทะเบียนแล้ว")
                    else:
                        with st.spinner("⏳ กำลังบันทึกข้อมูล... กรุณารอสักครู่"):
                            l_face = upload_to_drive(p_face, f"{std_id}_Face.jpg")
                            l_back = upload_to_drive(p_back, f"{std_id}_Back.jpg")
                            l_side = upload_to_drive(p_side, f"{std_id}_Side.jpg") if p_side else ""
                            sheet.append_row([
                                datetime.now().strftime('%d/%m/%Y %H:%M'), f"{prefix}{fname}", str(std_id), 
                                f"{level}/{room}", brand, color, plate, ls, ts, hs, 
                                l_back, l_side, "", "100", l_face, str(pin)
                            ])
                            st.session_state.reg_success = True
                            st.rerun()
                except Exception as e: st.error(f"เกิดข้อผิดพลาด: {e}")

    c1, c2 = st.columns(2)
    if c1.button("🆔 โหลดบัตรอนุญาต (Student Portal)", use_container_width=True): go_to_page('portal')
    if c2.button("🔐 เจ้าหน้าที่เข้าสู่ระบบ", use_container_width=True): go_to_page('teacher')

elif st.session_state['page'] == 'portal':
    if st.button("🏠 กลับหน้าหลัก", use_container_width=True): go_to_page('student')
    st.markdown("<h2 style='text-align:center;'>🆔 Student Digital Permit</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("ยืนยันตัวตนเพื่อดูบัตร")
        with st.form("portal_login"):
            sid = st.text_input("รหัสนักเรียน กรณีไม่ใช่นักเรียนกรอกวันเกิดเช่น 02092530")
            spin = st.text_input("รหัส PIN 6 หลัก", type="password", max_chars=6)
            if st.form_submit_button("🔓 แสดงบัตร", use_container_width=True, type="primary"):
                if sid and spin:
                    try:
                        sheet = connect_gsheet(); all_data = sheet.get_all_values()
                        headers = all_data[0]; df_all = pd.DataFrame(all_data[1:], columns=headers)
                        user = df_all[(df_all.iloc[:, 2] == sid) & (df_all.iloc[:, 15] == spin)]
                        if not user.empty:
                            st.session_state.portal_user = user.iloc[0].tolist()
                        else: st.error("❌ ข้อมูลไม่ถูกต้อง")
                    except Exception as e: st.error(f"ระบบขัดข้อง: {e}")
        
        if 'portal_user' in st.session_state:
            v = st.session_state.portal_user
            logo_b64 = img_to_b64(logo_path) if logo_path else ""
            face_url = get_img_link(v[14]) if len(v) > 14 and v[14] else "https://via.placeholder.com/100"
            score = int(v[13]) if len(v) > 13 and str(v[13]).isdigit() else 100
            score_color = "#16a34a" if score >= 80 else ("#ca8a04" if score >= 50 else "#dc2626")
            card_html = f"""
            <div class="atm-card">
                <div class="atm-header">
                    <img src="data:image/png;base64,{logo_b64}" class="atm-logo" onerror="this.style.display='none'">
                    <div class="atm-title">
                        <div class="atm-school-name">โรงเรียนโพนทองพัฒนาวิทยา</div>
                        <div class="atm-card-name">บัตรอนุญาตนำรถเข้าสถานศึกษา</div>
                    </div>
                </div>
                <div class="atm-body">
                    <img src="{face_url}" class="atm-photo" alt="Student Photo">
                    <div class="atm-info">
                        <div style="font-size:16px; font-weight:bold; color:#0f172a;">{v[1]}</div>
                        <div>รหัส: <b>{v[2]}</b></div>
                        <div>ระดับชั้น: <b>{v[3]}</b></div>
                        <div style="margin-top:5px; font-size:12px; color:#64748b;">เลขทะเบียนรถ</div>
                        <div style="font-family:monospace; font-size:18px; font-weight:bold; letter-spacing:1px; color:#1e293b;">{v[6]}</div>
                    </div>
                </div>
                <div class="atm-score-box">
                    <div class="atm-score-label">แต้มวินัยจราจร</div>
                    <div class="atm-score-val" style="color:{score_color};">{score}</div>
                </div>
                <div class="atm-disclaimer">*ไม่อาจใช้ทดแทนใบขับขี่ได้ตามกฎหมาย</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            st.write(""); st.info("💡 ปรับเป็นแนวนอนเพื่อให้นักเรียนบันทึกหน้าจอนี้(Capture) ไว้ให้ตรวจสอบ")

elif st.session_state['page'] == 'dashboard':
    if st.button("⬅️ กลับหน้าจัดการ", use_container_width=True): go_to_page('teacher')
    st.subheader("📊 สถิติจราจร")
    if 'df' in st.session_state:
        df = st.session_state.df.copy()
        df.columns = [f"Col_{i}_{name}" for i, name in enumerate(df.columns)]
        score_col = df.columns[13]; class_col = df.columns[3]
        df[score_col] = pd.to_numeric(df[score_col], errors='coerce').fillna(100)
        df['LV'] = df[class_col].apply(lambda x: str(x).split('/')[0])
        c1, c2, c3 = st.columns(3)
        with c1: st.plotly_chart(px.pie(df, names=df.columns[7], title="ใบขับขี่", hole=0.3), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df, names=df.columns[8], title="ภาษี/พรบ", hole=0.3), use_container_width=True)
        with c3: st.plotly_chart(px.pie(df, names=df.columns[9], title="หมวก", hole=0.3), use_container_width=True)
        c4, c5 = st.columns(2)
        with c4: st.plotly_chart(px.bar(df[['LV', score_col]].groupby('LV').mean().reset_index(), x='LV', y=score_col, title="คะแนนเฉลี่ย"), use_container_width=True)
        with c5: st.plotly_chart(px.bar(df.groupby('LV').size().reset_index(name='จำนวน'), x='LV', y='จำนวน', title="จำนวนรถ"), use_container_width=True)

elif st.session_state['page'] == 'edit':
    st.subheader("✏️ แก้ไขข้อมูล")
    v = st.session_state.edit_data
    with st.form("ed"):
        nm = st.text_input("ชื่อ", v[1]); cl = st.text_input("ชั้น", v[3]); br = st.selectbox("ยี่ห้อ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"]); co = st.text_input("สี", v[5]); pl = st.text_input("ทะเบียน", v[6])
        lc = st.radio("ใบขับขี่", ["✅ มี", "❌ ไม่มี"], index=0 if "มี" in v[7] else 1, horizontal=True); tx = st.radio("ภาษี", ["✅ ปกติ", "❌ ขาด"], index=0 if "ปกติ" in v[8] or "✅" in v[8] else 1, horizontal=True); hl = st.radio("หมวก", ["✅ มี", "❌ ไม่มี"], index=0 if "มี" in v[9] else 1, horizontal=True)
        nf = st.file_uploader("เปลี่ยนรูปหลัง"); ns = st.file_uploader("เปลี่ยนรูปข้าง")
        if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
            sheet = connect_gsheet(); cell = sheet.find(str(v[2])); l1, l2 = v[10], v[11]
            if nf: l1 = upload_to_drive(nf, f"{v[2]}_F_n.jpg"); 
            if ns: l2 = upload_to_drive(ns, f"{v[2]}_S_n.jpg")
            sheet.update(f'B{cell.row}:L{cell.row}', [[nm, v[2], cl, br, co, pl, lc, tx, hl, l1, l2]])
            load_data()
            st.success("เสร็จสิ้น"); st.session_state.edit_data = None; go_to_page('teacher')
    if st.button("ยกเลิก", use_container_width=True): go_to_page('teacher')

elif st.session_state['page'] == 'teacher':
    if st.button("🏠 กลับหน้าหลัก", use_container_width=True): go_to_page('student')
    
    if not st.session_state.get('logged_in'):
        with st.form("login_form"):
            st.header("🔐 เข้าสู่ระบบเจ้าหน้าที่")
            pwd = st.text_input("รหัสผ่านประจำตัวเจ้าหน้าที่", type="password")
            if st.form_submit_button("เข้าสู่ระบบ", use_container_width=True, type="primary"):
                if pwd in OFFICER_ACCOUNTS:
                    user_info = OFFICER_ACCOUNTS[pwd]
                    st.session_state.logged_in = True
                    st.session_state.officer_name = user_info["name"]
                    st.session_state.officer_role = user_info["role"]
                    st.session_state.current_user_pwd = pwd
                    st.session_state.last_active = time.time()
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if 'df' not in st.session_state: load_data()

        col_user, col_logout = st.columns([3, 1])
        col_user.info(f"👤 ผู้ใช้งาน: {st.session_state.officer_name} (สิทธิ์: {st.session_state.officer_role})")
        if col_logout.button("🚪 ออกจากระบบ", key="main_logout", use_container_width=True):
            logout()

        c1, c2 = st.columns(2)
        if c1.button("🔄 ดึงข้อมูลล่าสุด", use_container_width=True):
            load_data()
            st.session_state.search_results_df = None
        if c2.button("📊 รายงานสถิติ", use_container_width=True): go_to_page('dashboard')
        
        if 'df' in st.session_state:
            df = st.session_state.df
            total = len(df); lok = df[df.iloc[:,7].str.contains("มี", na=False)].shape[0]; tok = df[df.iloc[:,8].str.contains("ปกติ|✅", na=False)].shape[0]; hok = df[df.iloc[:,9].str.contains("มี", na=False)].shape[0]
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f'<div class="metric-card"><div class="metric-value">{total}</div><div class="metric-percent">100%</div><div class="metric-label">รถทั้งหมด</div></div>', unsafe_allow_html=True)
            with m2: p = (lok/total*100) if total else 0; st.markdown(f'<div class="metric-card"><div class="metric-value">{lok}</div><div class="metric-percent">{p:.1f}%</div><div class="metric-label">ใบขับขี่</div></div>', unsafe_allow_html=True)
            with m3: p = (tok/total*100) if total else 0; st.markdown(f'<div class="metric-card"><div class="metric-value">{tok}</div><div class="metric-percent">{p:.1f}%</div><div class="metric-label">ภาษี</div></div>', unsafe_allow_html=True)
            with m4: p = (hok/total*100) if total else 0; st.markdown(f'<div class="metric-card"><div class="metric-value">{hok}</div><div class="metric-percent">{p:.1f}%</div><div class="metric-label">หมวก</div></div>', unsafe_allow_html=True)
            
            st.markdown("---")
            q = st.text_input("🔍 ค้นหา (ชื่อ/รหัส/ทะเบียน)", on_change=reset_results)
            if q or (st.button("ค้นหา", use_container_width=True, type="primary") and q):
                if st.session_state.get('reset_count', 0) > 0:
                    with st.spinner("กำลังอัปเดตข้อมูล..."):
                        load_data()
                
                df = st.session_state.df
                st.session_state.search_results_df = df[df.iloc[:, [1, 2, 6]].apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)]
                st.session_state.preserve_search = True 
            
            st.write("")
            col_f1, col_f2, col_f3 = st.columns(3)
            f_risk = col_f1.selectbox("🚨 กรองกลุ่มปัญหา:", ["ทั้งหมด", "❌ ไม่มีใบขับขี่", "❌ ภาษีขาด", "❌ ไม่สวมหมวก"], on_change=reset_results)
            f_lv = col_f2.selectbox("📚 ระดับชั้น:", ["ทั้งหมด"] + sorted(list(set([str(x).split('/')[0] for x in df.iloc[:, 3].unique()]))), on_change=reset_results)
            f_br = col_f3.selectbox("🏍️ ยี่ห้อรถ:", ["ทั้งหมด"] + sorted(list(set(df.iloc[:, 4].unique()))), on_change=reset_results)
            
            if st.button("⚡ กรองข้อมูลตามเงื่อนไข", use_container_width=True):
                fdf = df.copy()
                if f_risk != "ทั้งหมด": idx = 7 if "ใบขับขี่" in f_risk else (8 if "ภาษี" in f_risk else 9); fdf = fdf[fdf.iloc[:, idx].astype(str).str.contains("ไม่มี|ขาด")]
                if f_lv != "ทั้งหมด": fdf = fdf[fdf.iloc[:, 3].astype(str).str.contains(f_lv)]
                if f_br != "ทั้งหมด": fdf = fdf[fdf.iloc[:, 4] == f_br]
                st.session_state.search_results_df = fdf

            if st.session_state.search_results_df is not None:
                if st.session_state.search_results_df.empty: st.warning("❌ ไม่พบข้อมูลที่ค้นหา")
                else:
                    for i, row in st.session_state.search_results_df.iterrows():
                        v = row.tolist(); sc = int(v[13]) if len(v)>13 and str(v[13]).isdigit() else 100
                        sc_color = "#22c55e" if sc >= 80 else ("#eab308" if sc >= 50 else "#ef4444")
                        
                        with st.expander(f"📍 {v[6]} | {v[1]}"):
                            c1, c2 = st.columns([1.5, 1])
                            with c1:
                                st.markdown(f"### 👤 {v[1]}")
                                st.caption(f"🆔 รหัส: {v[2]} | 📚 ชั้น: {v[3]}")
                            with c2:
                                st.markdown(f"### 🏍️ {v[6]}")
                                st.caption(f"{v[4]} ({v[5]})")

                            lic_ok = "มี" in str(v[7])
                            tax_ok = "ปกติ" in str(v[8]) or "✅" in str(v[8])
                            helm_ok = "มี" in str(v[9])
                            
                            st.markdown(f"""
                                <div style="display: flex; gap: 10px; margin: 10px 0;">
                                    <span style="background:{'#dcfce7' if lic_ok else '#fee2e2'}; color:{'#166534' if lic_ok else '#991b1b'}; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                                        {'✅' if lic_ok else '❌'} ใบขับขี่
                                    </span>
                                    <span style="background:{'#dcfce7' if tax_ok else '#fee2e2'}; color:{'#166534' if tax_ok else '#991b1b'}; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                                        {'✅' if tax_ok else '❌'} ภาษี
                                    </span>
                                    <span style="background:{'#dcfce7' if helm_ok else '#fee2e2'}; color:{'#166534' if helm_ok else '#991b1b'}; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                                        {'✅' if helm_ok else '❌'} หมวก
                                    </span>
                                </div>
                            """, unsafe_allow_html=True)

                            st.markdown(f"""
                                <div style="margin-top: 10px; margin-bottom: 5px;">
                                    <div style="display: flex; justify-content: space-between; align-items: end;">
                                        <span style="font-weight: bold; color: #64748b; font-size: 14px;">คะแนนความประพฤติ</span>
                                        <span style="font-size: 1.2rem; font-weight: 800; color: {sc_color};">{sc} / 100</span>
                                    </div>
                                    <div style="width: 100%; height: 10px; background-color: #e2e8f0; border-radius: 5px; overflow: hidden;">
                                        <div style="width: {sc}%; height: 100%; background-color: {sc_color}; border-radius: 5px;"></div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            st.divider()

                            c_img1, c_img2, c_img3 = st.columns(3)
                            with c_img1:
                                st.caption("👤 เจ้าของรถ")
                                if len(v)>14 and v[14]: st.image(get_img_link(v[14]), use_container_width=True)
                                else: st.info("ไม่มีรูป")
                            with c_img2:
                                st.caption("🏍️ ด้านหลัง")
                                st.image(get_img_link(v[10]), use_container_width=True)
                            with c_img3:
                                st.caption("🏍️ ด้านข้าง")
                                st.image(get_img_link(v[11]), use_container_width=True)
                            
                            face_url = get_img_link(v[14]) if len(v) > 14 else None
                            
                            if st.session_state.officer_role == "admin":
                                col_act1, col_act2 = st.columns(2)
                                col_act1.download_button("📥 โหลดใบประวัติ (PDF)", create_pdf(v, get_img_link(v[10]), get_img_link(v[11]), face_url, st.session_state.officer_name), f"{v[6]}.pdf", use_container_width=True)
                                if col_act2.button("✏️ แก้ไขข้อมูล", key=f"e_{i}", use_container_width=True): st.session_state.edit_data = v; go_to_page('edit')
                                
                                st.write("---")
                                st.caption("จัดการคะแนน:")
                                with st.form(key=f"score_form_{i}"):
                                    pts = st.number_input("จำนวนแต้ม", 1, 50, 5)
                                    note = st.text_area("เหตุผลการปรับคะแนน (จำเป็น)")
                                    pwd = st.text_input("ใส่รหัสผ่านของท่านเพื่อยืนยัน", type="password")
                                    
                                    col_sub1, col_sub2 = st.columns(2)
                                    submit_deduct = col_sub1.form_submit_button("🔴 หักแต้ม", use_container_width=True)
                                    submit_add = col_sub2.form_submit_button("🟢 เพิ่มแต้ม", use_container_width=True)

                                    if submit_deduct:
                                        if note and pwd == st.session_state.current_user_pwd:
                                            s = connect_gsheet(); cell = s.find(str(v[2])); ns = max(0, sc-pts)
                                            tn = (datetime.now()+timedelta(hours=7)).strftime('%d/%m/%Y %H:%M')
                                            old = str(v[12]).strip() if str(v[12]).lower()!="nan" else ""
                                            editor = st.session_state.officer_name
                                            new_log = f"{old}\n[{tn}] หัก {pts} คะแนน: {note} (โดย: {editor})"
                                            s.update(f'M{cell.row}:N{cell.row}', [[new_log, str(ns)]])
                                            st.session_state.reset_count += 1
                                            load_data()
                                            st.success("บันทึกแล้ว"); time.sleep(1); st.rerun()
                                        else: st.error("ข้อมูลไม่ครบ หรือ รหัสผ่านยืนยันไม่ถูกต้อง")
                                    
                                    if submit_add:
                                        if note and pwd == st.session_state.current_user_pwd:
                                            s = connect_gsheet(); cell = s.find(str(v[2])); ns = min(100, sc+pts)
                                            tn = (datetime.now()+timedelta(hours=7)).strftime('%d/%m/%Y %H:%M')
                                            old = str(v[12]).strip() if str(v[12]).lower()!="nan" else ""
                                            editor = st.session_state.officer_name
                                            new_log = f"{old}\n[{tn}] เพิ่ม {pts} คะแนน: {note} (โดย: {editor})"
                                            s.update(f'M{cell.row}:N{cell.row}', [[new_log, str(ns)]])
                                            st.session_state.reset_count += 1
                                            load_data()
                                            st.success("บันทึกแล้ว"); time.sleep(1); st.rerun()
                            else:
                                st.info("🔒 ท่านไม่มีสิทธิ์แก้ไขข้อมูลหรือดาวน์โหลดเอกสาร")
                                    
            st.markdown("---")
            # ตรวจสอบจาก Role แทน (ต้องไปตั้งค่าใน secrets.toml ให้ user นี้มี role เป็น 'super_admin')
if st.session_state.officer_role == "super_admin":
                with st.expander("⚙️ ระบบจัดการเลื่อนชั้นเรียน (Super Admin Only)"):
                    st.warning("⚠️ คำเตือน: การเลื่อนชั้นจะปรับระดับชั้นของนักเรียนทุกคน และไม่สามารถย้อนกลับได้ กรุณาตรวจสอบให้แน่ใจก่อนดำเนินการ")
                    up_pwd = st.text_input("รหัสเลื่อนชั้น", type="password", key="prom_pwd")
                    if st.button("ยืนยันเลื่อนชั้น", use_container_width=True) and up_pwd == UPGRADE_PASSWORD:
                        s = connect_gsheet(); d = s.get_all_values(); h = d[0]; r = d[1:]; nr = []
                        for row in r:
                            ol = str(row[3]); nl = ol
                            if "ม.1" in ol: nl=ol.replace("ม.1","ม.2")
                            elif "ม.2" in ol: nl=ol.replace("ม.2","ม.3")
                            elif "ม.3" in ol: nl="จบการศึกษา 🎓"
                            elif "ม.4" in ol: nl=ol.replace("ม.4","ม.5")
                            elif "ม.5" in ol: nl=ol.replace("ม.5","ม.6")
                            elif "ม.6" in ol: nl="จบการศึกษา 🎓"
                            row[3] = nl; nr.append(row)
                        s.clear(); s.update('A1', [h] + nr); st.success("สำเร็จ!"); del st.session_state.df
