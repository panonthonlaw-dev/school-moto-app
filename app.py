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
ADMIN_PASSWORD = "Patwit1150" 
UPGRADE_PASSWORD = "Patwitnext" 
GAS_APP_URL = "https://script.google.com/macros/s/AKfycbxRf6z032SxMkiI4IxtUBvWLKeo1LmIQAUMByoXidy4crNEwHoO6h0B-3hT0X7Q5g/exec" 

# --- 2. Setup หน้าเว็บ ---
st.set_page_config(page_title="patwit moto.", page_icon="logo", layout="wide")

def img_to_b64(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

st.markdown("""
    <style>
        header { visibility: hidden !important; height: 0px !important; }
        footer { visibility: hidden !important; height: 0px !important; }
        [data-testid="stSidebar"] { display: none; }
        .block-container { padding-top: 2rem; }
        .metric-card {
            background-color: #ffffff; padding: 15px; border-radius: 10px;
            border: 1px solid #e2e8f0; text-align: center;
        }
        .metric-value { font-size: 2.2rem; font-weight: bold; color: #1e293b; }
        .metric-percent { font-size: 1.1rem; color: #16a34a; font-weight: bold; }
        .score-display {
            font-size: 1.5rem; font-weight: bold; color: #ef4444;
            background: #fee2e2; padding: 10px; border-radius: 8px; text-align: center;
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
    </style>
""", unsafe_allow_html=True)

# --- 3. ฟังก์ชันระบบ ---
if 'page' not in st.session_state: st.session_state['page'] = 'student'
if 'search_results_df' not in st.session_state: st.session_state['search_results_df'] = None
if 'edit_data' not in st.session_state: st.session_state['edit_data'] = None

# ฟังก์ชันสำหรับรีเซ็ตฟอร์มเฉพาะตอนบันทึกสำเร็จ
def clear_form_state():
    keys_to_clear = ["reg_fname", "reg_id", "reg_room", "reg_pin", "reg_brand", "reg_color", "reg_plate"]
    for key in keys_to_clear:
        if key in st.session_state:
            st.session_state[key] = ""

def reset_results(): st.session_state['search_results_df'] = None
def go_to_page(page_name): st.session_state['page'] = page_name; st.rerun()

def connect_gsheet():
    key_content = st.secrets["textkey"]["json_content"]
    try: key_dict = json.loads(key_content, strict=False)
    except: key_dict = json.loads(key_content.replace('\n', '\\n'), strict=False)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

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

def create_pdf(vals, img_url1, img_url2):
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
    c.setFont(font_name, 16); c.drawString(60, height - 115, f"ชื่อ-นามสกุล: {name}"); c.drawString(330, height - 115, f"ยี่ห้อรถ: {brand}")
    c.drawString(60, height - 135, f"รหัสนักเรียน: {std_id}"); c.drawString(330, height - 135, f"สีรถ: {color}")
    c.drawString(60, height - 155, f"ระดับชั้น: {classroom}"); c.setFont(font_bold, 16); c.drawString(330, height - 155, f"ทะเบียน: {plate}")
    c.setFont(font_bold, 18); color_val = (0.7, 0, 0) if int(score) < 80 else (0, 0.5, 0); c.setFillColorRGB(*color_val)
    c.drawString(60, height - 185, f"คะแนนความประพฤติจราจรคงเหลือ: {score} คะแนน"); c.setFillColorRGB(0, 0, 0)
    c.setFont(font_name, 16); lm = "(/)" if "มี" in lic_s else "( )"; tm = "(/)" if "ปกติ" in tax_s or "✅" in tax_s else "( )"; hm = "(/)" if "มี" in hel_s else "( )"
    c.drawString(60, height - 210, f"สถานะเอกสาร:  {lm} ใบขับขี่    {tm} ภาษี/พรบ.    {hm} หมวกกันน็อค")
    def draw_img(url, x, y):
        try:
            if url and "drive.google.com" in url:
                res = requests.get(url, timeout=5)
                c.drawImage(ImageReader(io.BytesIO(res.content)), x, y, width=180, height=180, preserveAspectRatio=True)
        except: pass
    draw_img(img_url1, 70, height - 415); draw_img(img_url2, 300, height - 415)
    note_y = height - 455; c.setFont(font_bold, 16); c.drawString(60, note_y, "ประวัติบันทึกการทำผิดวินัยจราจร:")
    c.setFont(font_name, 15); text_obj = c.beginText(70, note_y - 25); text_obj.setLeading(20)
    for line in note_text.split('\n'):
        for w_line in textwrap.wrap(line, width=75): text_obj.textLine(w_line)
    c.drawText(text_obj)
    sign_y = 90; c.setFont(font_name, 16); c.drawString(60, sign_y, "ลงชื่อ ......................................... เจ้าของรถ"); c.drawString(100, sign_y - 20, f"({name})")
    c.drawString(320, sign_y, "ลงชื่อ ......................................... ครูผู้ตรวจสอบ")
    c.save(); buffer.seek(0); return buffer

# --- 4. Main UI ---
c_logo, c_title = st.columns([1, 8])
logo_path = next((f for f in ["logo.png", "logo.jpg", "logo"] if os.path.exists(f)), None)
with c_logo:
    if logo_path: st.image(logo_path, width=90)
    else: st.write("🏍️")
with c_title: st.title("ระบบลงทะเบียนรถจักรยานยนต์โรงเรียนโพนทองพัฒนาวิทยา")
st.markdown("---")

if st.session_state['page'] == 'student':
    st.info("📝 ลงทะเบียนรถและทำบัตรอนุญาตดิจิทัล")
    # ใช้ clear_on_submit=False เพื่อไม่ให้ข้อมูลหายถ้ากรอกผิด
    with st.form("reg_form", clear_on_submit=False):
        sc1, sc2 = st.columns(2)
        with sc1:
            prefix = st.selectbox("คำนำหน้า", ["นาย", "นางสาว", "เด็กชาย", "เด็กหญิง", "นาง", "ครู"])
            fname = st.text_input("ชื่อ-นามสกุล", key="reg_fname")
        std_id = sc2.text_input("รหัสนักเรียน/รหัสบุคลากร (สำคัญ)", key="reg_id")
        sc3, sc4 = st.columns(2)
        level = st.selectbox("ชั้น", ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6", "ครู,บุคลากร", "พ่อค้าแม่ค้า"])
        room = st.text_input("ห้อง (0-13)", key="reg_room")
        
        st.write("🔐 **ตั้งค่าความปลอดภัย**")
        pin = st.text_input("ตั้งรหัส PIN 6 หลัก (สำหรับโหลดบัตร)", type="password", max_chars=6, key="reg_pin", help="ห้ามใช้เลขซ้ำกันทั้งหมด")
        
        sc5, sc6 = st.columns(2)
        brand = st.selectbox("ยี่ห้อ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"], key="reg_brand")
        color = st.text_input("สีรถ", key="reg_color")
        plate = st.text_input("ทะเบียนรถ", placeholder="เช่น 1กข 1234", key="reg_plate")
        
        doc_cols = st.columns(3)
        ls = doc_cols[0].radio("ใบขับขี่", ["✅ มี", "❌ ไม่มี"], horizontal=True)
        ts = doc_cols[1].radio("ภาษี/พรบ", ["✅ ปกติ", "❌ ขาด"], horizontal=True)
        hs = doc_cols[2].radio("หมวกกันน็อค", ["✅ มี", "❌ ไม่มี"], horizontal=True)
        
        st.write("📸 **อัปโหลดภาพ (จำเป็น)**")
        up1, up2, up3 = st.columns(3)
        p_face = up1.file_uploader("1. หน้าตรงเจ้าของรถ", type=['jpg','png','jpeg'])
        p_back = up2.file_uploader("2. หลังรถ (เห็นป้าย)", type=['jpg','png','jpeg'])
        p_side = up3.file_uploader("3. ข้างรถ (เต็มคัน)", type=['jpg','png','jpeg'])
        
        pdpa = st.checkbox("ข้าพเจ้ายินยอมให้โรงเรียนเก็บข้อมูลและรูปภาพเพื่อใช้ในระบบรักษาความปลอดภัยจราจร")

        if st.form_submit_button("ส่งข้อมูลลงทะเบียน"):
            errors = []
            # ตรวจสอบข้อมูลทีละจุด
            if not fname: errors.append("ชื่อ-นามสกุล")
            if not std_id: errors.append("รหัสประจำตัว")
            if not plate: errors.append("ทะเบียนรถ")
            if not p_face: errors.append("รูปถ่ายหน้าตรง")
            if not p_back: errors.append("รูปถ่ายหลังรถ")
            
            # ตรวจสอบ PIN (ห้ามเลขซ้ำกันหมด)
            if not pin or len(pin) != 6 or not pin.isdigit():
                errors.append("รหัส PIN ต้องเป็นตัวเลข 6 หลัก")
            elif len(set(pin)) == 1:
                errors.append("รหัส PIN ห้ามใช้เลขซ้ำกันทั้งหมด (เช่น 111111)")
            
            if not pdpa: errors.append("การยอมรับเงื่อนไข (PDPA)")

            if errors:
                st.error(f"❌ กรุณากรอกข้อมูลให้ครบถ้วนและถูกต้อง: {', '.join(errors)}")
            else:
                try:
                    sheet = connect_gsheet()
                    if str(std_id) in sheet.col_values(3): st.error("❌ รหัสนี้เคยลงทะเบียนแล้ว ไม่สามารถลงซ้ำได้")
                    else:
                        with st.spinner("⏳ กำลังบันทึกข้อมูล..."):
                            l_face = upload_to_drive(p_face, f"{std_id}_Face.jpg")
                            l_back = upload_to_drive(p_back, f"{std_id}_Back.jpg")
                            l_side = upload_to_drive(p_side, f"{std_id}_Side.jpg") if p_side else ""
                            sheet.append_row([
                                datetime.now().strftime('%d/%m/%Y %H:%M'), f"{prefix}{fname}", str(std_id), 
                                f"{level}/{room}", brand, color, plate, ls, ts, hs, 
                                l_back, l_side, "", "100", l_face, str(pin)
                            ])
                            st.success("✅ ลงทะเบียนสำเร็จ! กรุณาจำรหัส PIN เพื่อใช้โหลดบัตร")
                            st.balloons()
                            clear_form_state() # ล้างค่าเมื่อสำเร็จ
                            time.sleep(2)
                            st.rerun()
                except Exception as e: st.error(f"เกิดข้อผิดพลาด: {e}")

    c1, c2 = st.columns(2)
    if c1.button("🆔 โหลดบัตรอนุญาต (Student Portal)", use_container_width=True): go_to_page('portal')
    if c2.button("🔐 เจ้าหน้าที่เข้าสู่ระบบ", use_container_width=True): go_to_page('teacher')

elif st.session_state['page'] == 'portal':
    if st.button("🏠 กลับหน้าหลัก"): go_to_page('student')
    st.markdown("<h2 style='text-align:center;'>🆔 Student Digital Permit</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("ยืนยันตัวตนเพื่อดูบัตร")
        sid = st.text_input("รหัสนักเรียน"); spin = st.text_input("รหัส PIN 6 หลัก", type="password", max_chars=6)
        if st.button("🔓 แสดงบัตร", use_container_width=True):
            if sid and spin:
                try:
                    sheet = connect_gsheet(); all_data = sheet.get_all_values()
                    headers = all_data[0]; df_all = pd.DataFrame(all_data[1:], columns=headers)
                    user = df_all[(df_all.iloc[:, 2] == sid) & (df_all.iloc[:, 15] == spin)]
                    if not user.empty:
                        v = user.iloc[0].tolist()
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
                        st.write(""); st.info("💡 ให้นักเรียนบันทึกหน้าจอนี้ (Capture) เพื่อแสดงต่อครูเวรหน้าประตูโรงเรียน")
                    else: st.error("❌ ข้อมูลไม่ถูกต้อง")
                except Exception as e: st.error(f"ระบบขัดข้อง: {e}")

elif st.session_state['page'] == 'dashboard':
    if st.button("⬅️ กลับ"): go_to_page('teacher')
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
    st.subheader("✏️ แก้ไข")
    v = st.session_state.edit_data
    with st.form("ed"):
        nm = st.text_input("ชื่อ", v[1]); cl = st.text_input("ชั้น", v[3]); br = st.selectbox("ยี่ห้อ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"]); co = st.text_input("สี", v[5]); pl = st.text_input("ทะเบียน", v[6])
        lc = st.radio("ใบขับขี่", ["✅ มี", "❌ ไม่มี"], index=0 if "มี" in v[7] else 1, horizontal=True); tx = st.radio("ภาษี", ["✅ ปกติ", "❌ ขาด"], index=0 if "ปกติ" in v[8] or "✅" in v[8] else 1, horizontal=True); hl = st.radio("หมวก", ["✅ มี", "❌ ไม่มี"], index=0 if "มี" in v[9] else 1, horizontal=True)
        nf = st.file_uploader("เปลี่ยนรูปหลัง"); ns = st.file_uploader("เปลี่ยนรูปข้าง")
        if st.form_submit_button("บันทึก"):
            sheet = connect_gsheet(); cell = sheet.find(str(v[2])); l1, l2 = v[10], v[11]
            if nf: l1 = upload_to_drive(nf, f"{v[2]}_F_n.jpg"); 
            if ns: l2 = upload_to_drive(ns, f"{v[2]}_S_n.jpg")
            sheet.update(f'B{cell.row}:L{cell.row}', [[nm, v[2], cl, br, co, pl, lc, tx, hl, l1, l2]]); st.success("เสร็จสิ้น"); del st.session_state.df; go_to_page('teacher')
    if st.button("ยกเลิก"): go_to_page('teacher')

elif st.session_state['page'] == 'teacher':
    if st.button("🏠 หน้าหลัก"): go_to_page('student')
    if not st.session_state.get('logged_in'):
        if st.button("Login") and st.text_input("Password", type="password") == ADMIN_PASSWORD: st.session_state.logged_in = True; st.rerun()
    else:
        c1, c2 = st.columns(2)
        if c1.button("🔄 ดึงข้อมูล"): vals = connect_gsheet().get_all_values(); st.session_state.df = pd.DataFrame(vals[1:], columns=[f"C{i}" for i, h in enumerate(vals[0])]) if len(vals)>1 else None; st.session_state.search_results_df = None
        if c2.button("📊 สถิติ"): go_to_page('dashboard')
        if 'df' in st.session_state:
            df = st.session_state.df
            t = len(df); l = df[df.iloc[:,7].str.contains("มี", na=False)].shape[0]; tx = df[df.iloc[:,8].str.contains("ปกติ|✅", na=False)].shape[0]; h = df[df.iloc[:,9].str.contains("มี", na=False)].shape[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card"><div class="metric-value">{t}</div><div class="metric-label">รถทั้งหมด</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div class="metric-value">{l}</div><div class="metric-label">ใบขับขี่</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card"><div class="metric-value">{tx}</div><div class="metric-label">ภาษี</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card"><div class="metric-value">{h}</div><div class="metric-label">หมวก</div></div>', unsafe_allow_html=True)
            q = st.text_input("ค้นหา", on_change=reset_results)
            if st.button("ค้นหา") and q: st.session_state.search_results_df = df[df.iloc[:, [1, 2, 6]].apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)]
            if st.session_state.search_results_df is not None:
                for i, row in st.session_state.search_results_df.iterrows():
                    v = row.tolist(); sc = int(v[13]) if len(v)>13 and str(v[13]).isdigit() else 100
                    with st.expander(f"📍 {v[6]} | {v[1]} (แต้ม: {sc})"):
                        ci, cd = st.columns([1, 2])
                        with ci: 
                            if len(v)>14 and v[14]: st.image(get_img_link(v[14]), width=120)
                        with cd:
                            st.download_button("PDF", create_pdf(v, get_img_link(v[10]), get_img_link(v[11])), f"{v[6]}.pdf")
                            if st.button("แก้ไข", key=f"e_{i}"): st.session_state.edit_data = v; go_to_page('edit')
                            pts = st.number_input("แต้ม", 1, 50, 5, key=f"p_{i}"); note = st.text_area("บันทึกเหตุผล", key=f"n_{i}"); pwd = st.text_input("รหัส", type="password", key=f"pw_{i}")
                            b1, b2 = st.columns(2)
                            if b1.button("🔴 หักแต้ม", key=f"s1_{i}"):
                                if note and pwd==UPGRADE_PASSWORD:
                                    s = connect_gsheet(); cell = s.find(str(v[2])); ns = max(0, sc-pts)
                                    tn = (datetime.now()+timedelta(hours=7)).strftime('%d/%m %H:%M')
                                    old = str(v[12]).strip() if str(v[12]).lower()!="nan" else ""
                                    s.update(f'M{cell.row}:N{cell.row}', [[f"{old}\n[{tn}] หัก {pts}: {note}", str(ns)]])
                                    st.success("บันทึกแล้ว"); time.sleep(1); st.rerun()
                                else: st.error("ใส่บันทึก/รหัสผิด")
                            if b2.button("🟢 เพิ่มแต้ม", key=f"s2_{i}"):
                                if note and pwd==UPGRADE_PASSWORD:
                                    s = connect_gsheet(); cell = s.find(str(v[2])); ns = min(100, sc+pts)
                                    tn = (datetime.now()+timedelta(hours=7)).strftime('%d/%m %H:%M')
                                    old = str(v[12]).strip() if str(v[12]).lower()!="nan" else ""
                                    s.update(f'M{cell.row}:N{cell.row}', [[f"{old}\n[{tn}] เพิ่ม {pts}: {note}", str(ns)]])
                                    st.success("บันทึกแล้ว"); time.sleep(1); st.rerun()
