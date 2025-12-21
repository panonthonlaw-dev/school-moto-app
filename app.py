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
        .digital-card {
            border: 2px solid #e2e8f0; border-radius: 15px; padding: 20px;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. ฟังก์ชันระบบ ---
if 'page' not in st.session_state: st.session_state['page'] = 'student'
if 'search_results_df' not in st.session_state: st.session_state['search_results_df'] = None
if 'edit_data' not in st.session_state: st.session_state['edit_data'] = None

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

# --- ฟังก์ชัน PDF (ประวัติสะสม) ---
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
    
    # ดึงประวัติบันทึกและคะแนน
    raw_note = str(vals[12]).strip() if len(vals) > 12 else ""
    note_text = raw_note if raw_note and raw_note.lower() != "nan" else "ไม่พบประวัติการทำผิดวินัย"
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

    # --- ส่วนบันทึก (Clean Text) ---
    note_y = height - 455
    c.setFont(font_bold, 16); c.drawString(60, note_y, "ประวัติบันทึกการทำผิดวินัยจราจรและข้อมูลเพิ่มเติม:")
    c.setFont(font_name, 15); text_obj = c.beginText(70, note_y - 25); text_obj.setLeading(20)
    for line in note_text.split('\n'):
        wrapped_lines = textwrap.wrap(line, width=75)
        for w_line in wrapped_lines: text_obj.textLine(w_line)
    c.drawText(text_obj)

    sign_y = 90; c.setFont(font_name, 16)
    c.drawString(60, sign_y, "ลงชื่อ ......................................... เจ้าของรถ"); c.drawString(100, sign_y - 20, f"({name})")
    c.drawString(320, sign_y, "ลงชื่อ ......................................... ครูผู้ตรวจสอบ")
    c.save(); buffer.seek(0); return buffer

# --- 4. Main App UI ---
c_logo, c_title = st.columns([1, 8])
with c_logo:
    logo_file = next((f for f in ["logo.png", "logo.jpg", "logo"] if os.path.exists(f)), None)
    if logo_file: st.image(logo_file, width=90)
    else: st.write("🏍️")
with c_title: st.title("ระบบลงทะเบียนรถจักรยานยนต์โรงเรียนโพนทองพัฒนาวิทยา")
st.markdown("---")

if st.session_state['page'] == 'student':
    st.info("📝 ลงทะเบียนรถและทำบัตรอนุญาตดิจิทัล")
    with st.form("reg_form", clear_on_submit=True):
        sc1, sc2 = st.columns(2)
        with sc1:
            prefix = st.selectbox("คำนำหน้า", ["นาย", "นางสาว", "เด็กชาย", "เด็กหญิง", "นาง", "ครู"])
            fname = st.text_input("ชื่อ-นามสกุล")
        std_id = sc2.text_input("รหัสนักเรียน/รหัสบุคลากร (สำคัญ)")
        sc3, sc4 = st.columns(2)
        level = st.selectbox("ชั้น", ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6", "ครู,บุคลากร", "พ่อค้าแม่ค้า"])
        room = st.text_input("ห้อง (0-13)")
        
        st.write("🔐 **ตั้งค่าความปลอดภัย**")
        pin = st.text_input("ตั้งรหัส PIN 6 หลัก (ใช้สำหรับโหลดบัตรอนุญาต)", type="password", max_chars=6, help="กรุณาจำรหัสนี้ไว้เพื่อใช้แสดงบัตร")
        
        sc5, sc6 = st.columns(2)
        brand = st.selectbox("ยี่ห้อรถ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"])
        plate = st.text_input("ทะเบียนรถ")
        
        st.write("📸 **อัปโหลดภาพถ่าย (จำเป็น)**")
        up1, up2, up3 = st.columns(3)
        p_face = up1.file_uploader("1. รูปหน้าตรงเจ้าของรถ", type=['jpg','png','jpeg'])
        p_back = up2.file_uploader("2. รูปหลังรถ (เห็นป้าย)", type=['jpg','png','jpeg'])
        p_side = up3.file_uploader("3. รูปข้างรถ (เต็มคัน)", type=['jpg','png','jpeg'])
        
        pdpa = st.checkbox("ข้าพเจ้ายินยอมให้โรงเรียนเก็บข้อมูลและรูปภาพเพื่อใช้ในระบบรักษาความปลอดภัยจราจร")

        if st.form_submit_button("ยืนยันการลงทะเบียน"):
            if fname and std_id and plate and pin and len(pin)==6 and p_face and p_back and pdpa:
                try:
                    sheet = connect_gsheet()
                    if str(std_id) in sheet.col_values(3): st.error("❌ รหัสนี้เคยลงทะเบียนแล้ว")
                    else:
                        with st.spinner("⏳ กำลังอัปโหลดข้อมูล..."):
                            l_face = upload_to_drive(p_face, f"{std_id}_Face.jpg")
                            l_back = upload_to_drive(p_back, f"{std_id}_Back.jpg")
                            l_side = upload_to_drive(p_side, f"{std_id}_Side.jpg") if p_side else ""
                            # บันทึกข้อมูล: Col 14 (O) = Face, Col 15 (P) = PIN
                            sheet.append_row([
                                datetime.now().strftime('%d/%m/%Y %H:%M'), f"{prefix}{fname}", str(std_id), 
                                f"{level}/{room}", brand, "-", plate, "✅ มี", "✅ ปกติ", "✅ มี", 
                                l_back, l_side, "", "100", l_face, str(pin)
                            ])
                            st.success("✅ ลงทะเบียนสำเร็จ! กรุณาจำรหัส PIN เพื่อใช้โหลดบัตร"); st.balloons()
                except Exception as e: st.error(f"Error: {e}")
            else: st.warning("⚠️ กรุณากรอกข้อมูลให้ครบ ถ่ายรูปให้ครบ 3 รูป และตั้งรหัส PIN 6 หลัก")
            
    # ปุ่มทางเลือก
    c_link1, c_link2 = st.columns(2)
    if c_link1.button("🆔 นักเรียน: โหลดบัตรอนุญาต (Student Portal)", use_container_width=True): go_to_page('portal')
    if c_link2.button("🔐 เจ้าหน้าที่: เข้าสู่ระบบ", use_container_width=True): go_to_page('teacher')

# --- หน้า Student Portal (ใหม่) ---
elif st.session_state['page'] == 'portal':
    if st.button("🏠 กลับหน้าหลัก"): go_to_page('student')
    st.markdown("<h2 style='text-align: center;'>🆔 Student Digital Permit Portal</h2>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("เข้าสู่ระบบเพื่อดูบัตรอนุญาต")
        sid = st.text_input("รหัสประจำตัวนักเรียน")
        spin = st.text_input("รหัส PIN 6 หลัก", type="password", max_chars=6)
        
        if st.button("🔓 แสดงบัตรอนุญาต", use_container_width=True):
            if sid and spin:
                try:
                    sheet = connect_gsheet(); all_data = sheet.get_all_values()
                    headers = all_data[0]; df_all = pd.DataFrame(all_data[1:], columns=headers)
                    # ตรวจสอบ ID และ PIN (Col index 2 และ 15)
                    user = df_all[(df_all.iloc[:, 2] == sid) & (df_all.iloc[:, 15] == spin)]
                    
                    if not user.empty:
                        v = user.iloc[0].tolist()
                        st.success(f"ยินดีต้อนรับ {v[1]}")
                        
                        # --- Digital Card Layout ---
                        st.markdown(f"""
                        <div class="digital-card">
                            <h3 style='text-align:center; color:#1e293b;'>โรงเรียนโพนทองพัฒนาวิทยา</h3>
                            <p style='text-align:center; color:#64748b;'>บัตรอนุญาตขับขี่รถจักรยานยนต์ในสถานศึกษา</p>
                            <hr>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        dc1, dc2 = st.columns([1, 2])
                        with dc1:
                            face_url = get_img_link(v[14]) if len(v) > 14 else None
                            if face_url: st.image(face_url, caption="ผู้ถือบัตร", use_container_width=True)
                            else: st.info("ไม่มีรูป")
                        with dc2:
                            st.markdown(f"**ชื่อ:** {v[1]}")
                            st.markdown(f"**รหัส:** {v[2]} | **ชั้น:** {v[3]}")
                            st.markdown(f"**รถ:** {v[4]} | **ทะเบียน:** {v[6]}")
                            
                            score = int(v[13]) if len(v) > 13 and str(v[13]).isdigit() else 100
                            color = "green" if score >= 80 else ("orange" if score >= 50 else "red")
                            st.markdown(f"<h1 style='color:{color};'>{score} คะแนน</h1>", unsafe_allow_html=True)
                            
                            if score < 50: st.error("⛔ ถูกระงับการอนุญาตชั่วคราว")
                            else: st.success("✅ สถานะ: อนุญาตให้ขับขี่")
                        
                        st.info("💡 ให้นักเรียนบันทึกหน้าจอนี้ (Capture) เพื่อแสดงต่อครูเวรหน้าประตูโรงเรียน")
                    else: st.error("❌ รหัสประจำตัว หรือ PIN ไม่ถูกต้อง")
                except Exception as e: st.error(f"Error: {e}")

elif st.session_state['page'] == 'dashboard':
    if st.button("⬅️ กลับหน้าจัดการ"): go_to_page('teacher')
    st.subheader("📊 รายงานวิเคราะห์วินัยจราจร")
    if 'df' in st.session_state:
        df = st.session_state.df.copy()
        df.columns = [f"Col_{i}_{name}" for i, name in enumerate(df.columns)]
        score_col = df.columns[13]; class_col = df.columns[3]
        df[score_col] = pd.to_numeric(df[score_col], errors='coerce').fillna(100)
        df['LV'] = df[class_col].apply(lambda x: str(x).split('/')[0])
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1: st.plotly_chart(px.pie(df, names=df.columns[7], title="🪪 ใบขับขี่รวม", hole=0.3), use_container_width=True)
        with p_col2: st.plotly_chart(px.pie(df, names=df.columns[8], title="📝 ภาษี/พรบ.", hole=0.3), use_container_width=True)
        with p_col3: st.plotly_chart(px.pie(df, names=df.columns[9], title="⛑️ หมวกกันน็อค", hole=0.3), use_container_width=True)
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            avg_s = df[['LV', score_col]].groupby('LV').mean().reset_index()
            st.plotly_chart(px.bar(avg_s, x='LV', y=score_col, title="⭐ คะแนนวินัยเฉลี่ยแยกชั้น"), use_container_width=True)
        with b_col2: st.plotly_chart(px.bar(df.groupby('LV').size().reset_index(name='จำนวน'), x='LV', y='จำนวน', title="📚 จำนวนรถแยกตามชั้น"), use_container_width=True)

elif st.session_state['page'] == 'edit':
    st.subheader("✏️ แก้ไขข้อมูล")
    v = st.session_state.edit_data
    with st.form("edit_form"):
        n_name = st.text_input("ชื่อ", value=v[1]); n_class = st.text_input("ชั้น/ห้อง", value=v[3])
        n_brand = st.selectbox("ยี่ห้อ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"], index=0)
        n_color = st.text_input("สี", value=v[5]); n_plate = st.text_input("ทะเบียน", value=v[6])
        n_lic = st.radio("ใบขับขี่", ["✅ มี", "❌ ไม่มี"], index=0 if "มี" in v[7] else 1, horizontal=True)
        n_tax = st.radio("ภาษี", ["✅ ปกติ", "❌ ขาด"], index=0 if "ปกติ" in v[8] or "✅" in v[8] else 1, horizontal=True)
        n_hel = st.radio("หมวก", ["✅ มี", "❌ ไม่มี"], index=0 if "มี" in v[9] else 1, horizontal=True)
        p1_new = st.file_uploader("เปลี่ยนรูปหลังรถ"); p2_new = st.file_uploader("เปลี่ยนรูปข้างรถ")
        if st.form_submit_button("บันทึก"):
            sheet = connect_gsheet(); cell = sheet.find(str(v[2])); l1, l2 = v[10], v[11]
            if p1_new: l1 = upload_to_drive(p1_new, f"{v[2]}_F_n.jpg")
            if p2_new: l2 = upload_to_drive(p2_new, f"{v[2]}_S_n.jpg")
            sheet.update(f'B{cell.row}:L{cell.row}', [[n_name, v[2], n_class, n_brand, n_color, n_plate, n_lic, n_tax, n_hel, l1, l2]])
            st.success("แก้ไขแล้ว!"); del st.session_state.df; go_to_page('teacher')
    if st.button("ยกเลิก"): go_to_page('teacher')

elif st.session_state['page'] == 'teacher':
    if st.button("🏠 กลับหน้าหลัก"): go_to_page('student')
    if not st.session_state.get('logged_in'):
        pwd = st.text_input("รหัสผ่านเจ้าหน้าที่", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD: st.session_state.logged_in = True; st.rerun()
            else: st.error("รหัสไม่ถูกต้อง")
    else:
        tc1, tc2 = st.columns(2)
        if tc1.button("🔄 ดึงข้อมูลล่าสุด", use_container_width=True):
            vals = connect_gsheet().get_all_values()
            if len(vals) > 1: st.session_state.df = pd.DataFrame(vals[1:], columns=[h if h else f"Empty_{i}" for i, h in enumerate(vals[0])]); st.session_state.search_results_df = None
        if tc2.button("📊 รายงานสถิติ", use_container_width=True): go_to_page('dashboard')

        if 'df' in st.session_state:
            df = st.session_state.df; total = len(df)
            lok = df[df.iloc[:, 7].astype(str).str.contains("✅ มี")].shape[0]; tok = df[df.iloc[:, 8].astype(str).str.contains("ปกติ|✅")].shape[0]; hok = df[df.iloc[:, 9].astype(str).str.contains("✅ มี")].shape[0]
            st.markdown("### 📊 สรุปผลวินัยจราจร")
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card"><div class="metric-value">{total}</div><div class="metric-percent">100%</div><div class="metric-label">🏍️ ทั้งหมด</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div class="metric-value">{lok}</div><div class="metric-percent">{(lok/total*100) if total>0 else 0:.1f}%</div><div class="metric-label">🪪 ใบขับขี่</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card"><div class="metric-value">{tok}</div><div class="metric-percent">{(tok/total*100) if total>0 else 0:.1f}%</div><div class="metric-label">📝 ภาษีปกติ</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card"><div class="metric-value">{hok}</div><div class="metric-percent">{(hok/total*100) if total>0 else 0:.1f}%</div><div class="metric-label">⛑️ หมวกกันน็อค</div></div>', unsafe_allow_html=True)

            st.markdown("---")
            q_txt = st.text_input("🔍 ค้นหา (ชื่อ/รหัส/ทะเบียน)", on_change=reset_results)
            if st.button("กดเพื่อค้นหา", use_container_width=True) and q_txt:
                st.session_state.search_results_df = df[df.iloc[:, [1, 2, 6]].apply(lambda r: r.astype(str).str.contains(q_txt, case=False).any(), axis=1)]
            
            st.write("---")
            col_f1, col_f2, col_f3 = st.columns(3)
            f_risk = col_f1.selectbox("🚨 กรองกลุ่มปัญหา:", ["ทั้งหมด", "❌ ไม่มีใบขับขี่", "❌ ภาษีขาด", "❌ ไม่สวมหมวก"], on_change=reset_results)
            f_lv = col_f2.selectbox("📚 ระดับชั้น:", ["ทั้งหมด"] + sorted(list(set([str(x).split('/')[0] for x in df.iloc[:, 3].unique()]))), on_change=reset_results)
            f_br = col_f3.selectbox("🏍️ ยี่ห้อรถ:", ["ทั้งหมด"] + sorted(list(set(df.iloc[:, 4].unique()))), on_change=reset_results)
            if st.button("⚡ กรองตามเงื่อนไข", use_container_width=True, type="primary"):
                fdf = df.copy()
                if f_risk != "ทั้งหมด": idx = 7 if "ใบขับขี่" in f_risk else (8 if "ภาษี" in f_risk else 9); fdf = fdf[fdf.iloc[:, idx].astype(str).str.contains("ไม่มี|ขาด")]
                if f_lv != "ทั้งหมด": fdf = fdf[fdf.iloc[:, 3].astype(str).str.contains(f_lv)]
                if f_br != "ทั้งหมด": fdf = fdf[fdf.iloc[:, 4] == f_br]
                st.session_state.search_results_df = fdf

            if st.session_state.search_results_df is not None:
                res = st.session_state.search_results_df
                if res.empty: st.warning("ไม่พบข้อมูล")
                else:
                    for i, row in res.iterrows():
                        v = row.tolist(); curr_score = int(v[13]) if len(v) > 13 and str(v[13]).isdigit() else 100
                        with st.expander(f"📍 {v[6]} | {v[1]} (แต้ม: {curr_score})", expanded=True):
                            c_im, c_in = st.columns([2, 1])
                            with c_im:
                                i1, i2 = get_img_link(v[10]), get_img_link(v[11])
                                sub1, sub2 = st.columns(2)
                                if i1: sub1.image(i1, caption="หลัง")
                                if i2: sub2.image(i2, caption="ข้าง")
                                # แสดงรูปหน้าตรง (ถ้ามี)
                                if len(v) > 14:
                                    face_url = get_img_link(v[14])
                                    if face_url: st.image(face_url, width=150, caption="รูปหน้าตรง")
                            with c_in:
                                st.markdown(f'<div class="score-display">คะแนนวินัย: {curr_score} แต้ม</div>', unsafe_allow_html=True)
                                st.download_button("⬇️ โหลด PDF", create_pdf(v, i1, i2), f"{v[6]}.pdf", key=f"pdf_{i}", mime="application/pdf")
                                if st.button("✏️ แก้ไขข้อมูลเบื้องต้น", key=f"e_{i}"): st.session_state.edit_data = v; go_to_page('edit')
                                st.write("---"); st.write("🛡️ **จัดการวินัยจราจร (ประวัติจะสะสมอัตโนมัติ)**")
                                points = st.number_input("จำนวนแต้มที่จะปรับ", min_value=1, max_value=50, value=5, key=f"pts_{i}")
                                nn = st.text_area("✍️ ระบุเหตุผล (จำเป็น)", key=f"n_{i}", placeholder="กรุณาระบุสาเหตุที่นี่...")
                                apwd = st.text_input("รหัสยืนยันการทำรายการ (Patwitnext)", type="password", key=f"apwd_{i}")
                                
                                col_sc1, col_sc2 = st.columns(2)
                                if col_sc1.button(f"🔴 หัก {points} แต้ม", key=f"sub_{i}", use_container_width=True):
                                    if not nn.strip(): st.warning("⚠️ กรุณากรอกเหตุผลก่อนดำเนินการ")
                                    elif apwd != UPGRADE_PASSWORD: st.error("❌ รหัสผิด")
                                    else:
                                        sheet = connect_gsheet(); cell = sheet.find(str(v[2]))
                                        new_s = max(0, curr_score - points)
                                        thai_now = (datetime.now()+timedelta(hours=7)).strftime('%d/%m/%y %H:%M')
                                        current_note = str(v[12]).strip() if str(v[12]).lower() != "nan" else ""
                                        new_entry = f"[{thai_now}] หัก {points} คะแนน: {nn}"
                                        combined_note = f"{current_note}\n{new_entry}" if current_note else new_entry
                                        sheet.update(f'M{cell.row}:N{cell.row}', [[combined_note, str(new_s)]])
                                        st.success("บันทึกสำเร็จ!"); time.sleep(1); st.rerun()

                                if col_sc2.button(f"🟢 เพิ่ม {points} แต้ม", key=f"add_{i}", use_container_width=True):
                                    if not nn.strip(): st.warning("⚠️ กรุณากรอกเหตุผลก่อนดำเนินการ")
                                    elif apwd != UPGRADE_PASSWORD: st.error("❌ รหัสผิด")
                                    else:
                                        sheet = connect_gsheet(); cell = sheet.find(str(v[2]))
                                        new_s = min(100, curr_score + points)
                                        thai_now = (datetime.now()+timedelta(hours=7)).strftime('%d/%m/%y %H:%M')
                                        current_note = str(v[12]).strip() if str(v[12]).lower() != "nan" else ""
                                        new_entry = f"[{thai_now}] เพิ่ม {points} คะแนน: {nn}"
                                        combined_note = f"{current_note}\n{new_entry}" if current_note else new_entry
                                        sheet.update(f'M{cell.row}:N{cell.row}', [[combined_note, str(new_s)]])
                                        st.success("บันทึกสำเร็จ!"); time.sleep(1); st.rerun()

            st.markdown("---")
            with st.expander("⚙️ ระบบจัดการเลื่อนชั้นเรียนประจำปี"):
                up_pwd = st.text_input("รหัสเลื่อนชั้น", type="password", key="prom_pwd")
                if st.button("ยืนยันเลื่อนชั้นทุกคน") and up_pwd == UPGRADE_PASSWORD:
                    sheet = connect_gsheet(); d = sheet.get_all_values(); h = d[0]; r = d[1:]; new_r = []
                    for row in r:
                        ol = str(row[3]); nl = ol
                        if "ม.1" in ol: nl=ol.replace("ม.1","ม.2")
                        elif "ม.2" in ol: nl=ol.replace("ม.2","ม.3")
                        elif "ม.3" in ol: nl="จบการศึกษา 🎓"
                        elif "ม.4" in ol: nl=ol.replace("ม.4","ม.5")
                        elif "ม.5" in ol: nl=ol.replace("ม.5","ม.6")
                        elif "ม.6" in ol: nl="จบการศึกษา 🎓"
                        row[3] = nl; new_r.append(row)
                    sheet.clear(); sheet.update('A1', [h] + new_r); st.success("สำเร็จ!"); del st.session_state.df
