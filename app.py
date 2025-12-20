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

# --- ส่วนของ PDF Library ---
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

# --- 1. ตั้งค่า (Config) ---
SHEET_NAME = "Motorcycle_DB"
DRIVE_FOLDER_ID = "1WQGATGaGBoIjf44Yj_-DjuX8LZ8kbmBA" 
ADMIN_PASSWORD = "Patwit1150" 
GAS_APP_URL = "https://script.google.com/macros/s/AKfycbxRf6z032SxMkiI4IxtUBvWLKeo1LmIQAUMByoXidy4crNEwHoO6h0B-3hT0X7Q5g/exec" 

# --- 2. Setup หน้าเว็บ ---
st.set_page_config(page_title="patwit moto.", page_icon="logo", layout="wide")

st.markdown("""
    <style>
        header { visibility: hidden !important; height: 0px !important; }
        footer { visibility: hidden !important; height: 0px !important; }
        [data-testid="stSidebar"] { display: none; }
        .block-container { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- 3. ฟังก์ชันระบบ ---
if 'page' not in st.session_state:
    st.session_state['page'] = 'student'

def go_to_teacher():
    st.session_state['page'] = 'teacher'

def go_to_student():
    st.session_state['page'] = 'student'

def get_creds():
    key_content = st.secrets["textkey"]["json_content"]
    try:
        key_dict = json.loads(key_content, strict=False)
    except json.JSONDecodeError:
        clean_content = key_content.replace('\n', '\\n')
        key_dict = json.loads(clean_content, strict=False)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)

def connect_gsheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def upload_to_drive(file_obj, filename):
    if "script.google.com" not in GAS_APP_URL:
        st.error("🚨 กรุณาใส่ URL Web App")
        return None
    try:
        file_content = file_obj.getvalue()
        base64_str = base64.b64encode(file_content).decode('utf-8')
        payload = {"folder_id": DRIVE_FOLDER_ID, "filename": filename, "file": base64_str, "mimeType": file_obj.type}
        response = requests.post(GAS_APP_URL, json=payload)
        result = response.json()
        if result.get("status") == "success": return result.get("link")
        else: raise Exception(f"Upload failed: {result.get('message')}")
    except Exception as e: raise Exception(f"เชื่อมต่อไม่ได้: {e}")

def get_img_link(url):
    url = str(url).strip()
    if not url: return None
    file_id = None
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match: file_id = match.group(1)
    else:
        match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if match: file_id = match.group(1)
    if file_id: return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"
    return url

def create_pdf(vals, img_url1, img_url2):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    try:
        pdfmetrics.registerFont(TTFont('THSarabunNew', 'THSarabunNew.ttf'))
        font_name = 'THSarabunNew'
    except: font_name = 'Helvetica'
    try: c.drawImage("logo", 50, height - 85, width=50, height=50, mask='auto')
    except: pass 
    
    c.setFont(font_name, 24)
    c.drawCentredString(width/2, height - 50, "แบบทะเบียนประวัติรถจักรยานยนต์นักเรียน")
    c.setFont(font_name, 20)
    c.drawCentredString(width/2, height - 75, "โรงเรียนโพนทองพัฒนาวิทยา")
    c.line(50, height - 90, width - 50, height - 90)
    
    c.setFont(font_name, 16)
    name, std_id, classroom, brand, color, plate = str(vals[1]), str(vals[2]), str(vals[3]), str(vals[4]), str(vals[5]), str(vals[6])
    lic_status, tax_status, helmet_status = str(vals[7]), str(vals[8]), str(vals[9])
    
    c.drawString(60, height - 130, f"ชื่อ-นามสกุล: {name}")
    c.drawString(320, height - 130, f"ยี่ห้อ: {brand}")
    c.drawString(60, height - 155, f"รหัสนักเรียน: {std_id}")
    c.drawString(320, height - 155, f"สีรถ: {color}")
    c.drawString(60, height - 180, f"ระดับชั้น: {classroom}")
    c.setFont(font_name, 18)
    c.drawString(320, height - 180, f"ทะเบียน: {plate}")
    
    c.setFont(font_name, 16)
    lic_mark = "(/)" if "มี" in lic_status else "( )"
    tax_mark = "(/)" if "ปกติ" in tax_status or "✅" in tax_status else "( )"
    helmet_mark = "(/)" if "มี" in helmet_status else "( )"
    c.drawString(60, height - 210, f"สถานะเอกสาร: {lic_mark} ใบขับขี่  {tax_mark} พรบ./ภาษี  {helmet_mark} หมวกกันน็อค")
    
    c.setFont(font_name, 16)
    c.drawString(60, height - 250, "หลักฐานภาพถ่าย:")
    img_y = height - 430 
    def draw_img(url, x, y):
        try:
            if url:
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    img = ImageReader(io.BytesIO(res.content))
                    c.drawImage(img, x, y, width=170, height=170, preserveAspectRatio=True)
                else: c.drawString(x, y + 80, "โหลดรูปไม่ได้")
        except: c.drawString(x, y + 80, "Error รูปภาพ")
    
    draw_img(img_url1, 80, img_y)
    draw_img(img_url2, 310, img_y)

    note_y = img_y - 40
    c.setFont(font_name, 16)
    c.drawString(60, note_y, "บันทึกข้อความเพิ่มเติม:")
    c.setDash(1, 2)
    for i in range(5):
        line_y = note_y - 25 - (i * 25)
        c.line(60, line_y, 530, line_y)
    c.setDash()

    y_sign = 85
    c.setFont(font_name, 16)
    c.drawString(60, y_sign, "ลงชื่อ ....................................................... เจ้าของรถ")
    c.drawString(100, y_sign - 20, f"({name})")
    c.drawString(300, y_sign, "ลงชื่อ ....................................................... ครูผู้ตรวจสอบ")
    c.drawString(330, y_sign - 20, "(.......................................................)")
    
    c.setFont(font_name, 10)
    thai_now = datetime.now() + timedelta(hours=7)
    c.drawRightString(width - 30, 20, f"พิมพ์เมื่อ: {thai_now.strftime('%d/%m/%Y %H:%M')}")
    c.save()
    buffer.seek(0)
    return buffer

# --- 4. Main App UI ---
c_logo, c_title = st.columns([1, 8])
with c_logo:
    try: st.image("logo", width=90)
    except: st.write("🏍️")
with c_title: st.title("ระบบลงทะเบียนรถจักรยานยนต์โรงเรียนโพนทองพัฒนาวิทยา")
st.markdown("---")

if st.session_state['page'] == 'student':
    st.info("📝 สำหรับนักเรียน: ลงทะเบียนข้อมูลรถ")
    with st.form("reg_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            sub_c1, sub_c2 = st.columns([1.2, 2])
            prefix = sub_c1.selectbox("คำนำหน้า", ["นาย", "นางสาว", "เด็กชาย", "เด็กหญิง", "นาง"])
            fname = sub_c2.text_input("ชื่อ-นามสกุล")
        std_id = c2.text_input("รหัสนักเรียน/รหัสเจ้าหน้าที่")
        c3, c4 = st.columns(2)
        level = c3.selectbox("ชั้น", ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6", "ครู,บุคลากร", "พ่อค้าแม่ค้า"])
        room = c4.text_input("ห้อง/เบอร์โทร")
        c5, c6 = st.columns(2)
        brand = c5.selectbox("ยี่ห้อ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"])
        color = c6.text_input("สีรถ")
        plate = st.text_input("ทะเบียน")
        
        doc_c1, doc_c2, doc_c3 = st.columns(3)
        license_status = doc_c1.radio("ใบขับขี่", ["✅ มี", "❌ ไม่มี"], horizontal=True)
        tax_status = doc_c2.radio("ภาษี/พรบ", ["✅ ปกติ", "❌ ขาด"], horizontal=True)
        helmet_status = doc_c3.radio("หมวกกันน็อค", ["✅ มี", "❌ ไม่มี"], horizontal=True)
        
        photo1 = st.file_uploader("รูปหลังรถ", type=['jpg','png','jpeg'])
        photo2 = st.file_uploader("รูปข้างรถ", type=['jpg','png','jpeg'])
        
        if st.form_submit_button("ส่งข้อมูลลงทะเบียน", use_container_width=True):
            if fname and std_id and plate and photo1:
                try:
                    sheet = connect_gsheet()
                    if str(std_id) in sheet.col_values(3): 
                        st.error("❌ รหัสนี้เคยลงทะเบียนไปแล้ว!")
                    else:
                        with st.spinner("⏳ กำลังบันทึกข้อมูล..."):
                            l1 = upload_to_drive(photo1, f"{std_id}_F.jpg")
                            l2 = upload_to_drive(photo2, f"{std_id}_S.jpg") if photo2 else ""
                            thai_now = datetime.now() + timedelta(hours=7)
                            full_name = f"{prefix}{fname}"
                            sheet.append_row([thai_now.strftime('%d/%m/%Y %H:%M'), full_name, str(std_id), f"{level}/{room}", brand, color, plate, license_status, tax_status, helmet_status, l1, l2])
                            st.balloons()
                            st.success("✅ ลงทะเบียนสำเร็จ!")
                except Exception as e: st.error(f"Error: {e}")
            else: st.warning("⚠️ กรุณากรอกข้อมูลให้ครบ")

    if st.button("🔐 สำหรับเจ้าหน้าที่", use_container_width=True):
        go_to_teacher(); st.rerun()

elif st.session_state['page'] == 'teacher':
    if st.button("🏠 กลับหน้าหลัก"): go_to_student(); st.rerun()
    if not st.session_state.get('logged_in'):
        pwd = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD: st.session_state.logged_in = True; st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if st.button("🚪 ออกจากระบบ"): st.session_state.logged_in = False; st.rerun()
        if st.button("🔄 ดึงข้อมูลล่าสุด", use_container_width=True):
            try:
                all_vals = connect_gsheet().get_all_values()
                if len(all_vals) > 1:
                    st.session_state.df = pd.DataFrame(all_vals[1:], columns=all_vals[0])
                    st.success("โหลดข้อมูลสำเร็จ")
                else:
                    st.session_state.df = pd.DataFrame(columns=["Timestamp","Name","ID","Class","Brand","Color","Plate","License","Tax","Helmet","Img1","Img2"])
                    st.warning("ยังไม่มีข้อมูล")
            except Exception as e: st.error(f"Error: {e}")
        
        if 'df' in st.session_state:
            df = st.session_state.df
            total = len(df)
            
            # --- ปรับแก้จุดนี้: ตรวจสอบข้อความตรงกับฟอร์มลงทะเบียน ---
            try:
                lic_count = df[df.iloc[:, 7].astype(str).str.contains("✅ มี", na=False)].shape[0]
                # เช็คคำว่า "✅ ปกติ" ให้ตรงกับ radio button ของหน้าลงทะเบียน
                tax_count = df[df.iloc[:, 8].astype(str).str.contains("✅ ปกติ", na=False)].shape[0]
                hel_count = df[df.iloc[:, 9].astype(str).str.contains("✅ มี", na=False)].shape[0]
                
                lic_p = (lic_count/total)*100 if total > 0 else 0
                tax_p = (tax_count/total)*100 if total > 0 else 0
                hel_p = (hel_count/total)*100 if total > 0 else 0
            except: lic_count, tax_count, hel_count, lic_p, tax_p, hel_p = 0, 0, 0, 0, 0, 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🏍️ รถทั้งหมด", f"{total} คัน")
            c2.metric("🪪 มีใบขับขี่", f"{lic_count} คน", f"{lic_p:.1f}%")
            c3.metric("📝 ภาษีปกติ", f"{tax_count} คัน", f"{tax_p:.1f}%")
            c4.metric("⛑️ หมวกกันน็อค", f"{hel_count} คน", f"{hel_p:.1f}%")

            q = st.text_input("🔍 ค้นหา (ชื่อ/รหัส/ทะเบียน)", key="search_query")
            if st.button("เริ่มการค้นหา") and q:
                fdf = df[df.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1)]
                if fdf.empty: st.warning("ไม่พบข้อมูล")
                else:
                    for i, row in fdf.iterrows():
                        v = row.tolist()
                        with st.expander(f"📍 {v[6]} | {v[1]}"):
                            c_img, c_info = st.columns([2, 1])
                            with c_img:
                                i1, i2 = get_img_link(v[10]), get_img_link(v[11])
                                sub_img1, sub_img2 = st.columns(2)
                                if i1: sub_img1.image(i1, caption="รูปหลังรถ")
                                if i2: sub_img2.image(i2, caption="รูปข้างรถ")
                            with c_info:
                                st.write(f"**รหัส:** {v[2]} | **ชั้น:** {v[3]}")
                                st.write(f"**ยี่ห้อ:** {v[4]} | **สี:** {v[5]}")
                                st.write(f"**เอกสาร:** {v[7]} / {v[8]} / {v[9]}")
                                pdf_data = create_pdf(v, i1, i2)
                                st.download_button("⬇️ โหลด PDF", pdf_data, f"Profile_{v[6]}.pdf", key=f"dl_{i}")
