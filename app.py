import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import requests
import base64

# --- ตั้งค่า (Config) ---
SHEET_NAME = "Motorcycle_DB"
DRIVE_FOLDER_ID = "1WQGATGaGBoIjf44Yj_-DjuX8LZ8kbmBA" 
ADMIN_PASSWORD = "Patwit064180"
GAS_APP_URL = "https://script.google.com/macros/s/AKfycbxRf6z032SxMkiI4IxtUBvWLKeo1LmIQAUMByoXidy4crNEwHoO6h0B-3hT0X7Q5g/exec" 

# --- Setup หน้าเว็บ และ ซ่อน Header แบบถาวร ---
st.set_page_config(page_title="patwit moto.", page_icon="logo", layout="wide")

st.markdown("""
    <style>
        /* ซ่อน Header และ Toolbar ด้านบนทั้งหมดแบบถาวร */
        header {
            visibility: hidden !important;
            height: 0px !important;
        }
        /* ซ่อน Footer */
        footer {
            visibility: hidden !important;
            height: 0px !important;
        }
        /* ซ่อน Sidebar (เผื่อมันโผล่มา) */
        [data-testid="stSidebar"] {
            display: none;
        }
        /* เพิ่มระยะด้านบนหน่อย เพราะพอซ่อน Header แล้วเนื้อหาจะติดขอบจอเกินไป */
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- State Management (ตัวกำหนดว่าจะโชว์หน้าไหน) ---
if 'page' not in st.session_state:
    st.session_state['page'] = 'student' # ค่าเริ่มต้นคือหน้านักเรียน

def go_to_teacher():
    st.session_state['page'] = 'teacher'

def go_to_student():
    st.session_state['page'] = 'student'

# --- เชื่อมต่อ Google Sheets (เหมือนเดิม) ---
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

# --- ฟังก์ชันอัปโหลด (เหมือนเดิม) ---
def upload_to_drive(file_obj, filename):
    if "script.google.com" not in GAS_APP_URL:
        st.error("🚨 กรุณาใส่ URL ของ Web App ในโค้ดบรรทัดที่ 16 ก่อนครับ")
        return None

    try:
        file_content = file_obj.getvalue()
        base64_str = base64.b64encode(file_content).decode('utf-8')
        
        payload = {
            "folder_id": DRIVE_FOLDER_ID,
            "filename": filename,
            "file": base64_str,
            "mimeType": file_obj.type
        }
        
        response = requests.post(GAS_APP_URL, json=payload)
        result = response.json()
        
        if result.get("status") == "success":
            return result.get("link")
        else:
            raise Exception(f"Upload failed: {result.get('message')}")
            
    except Exception as e:
        raise Exception(f"เชื่อมต่อไม่ได้: {e}")

# ==========================================
# 🟢 ส่วนแสดงผลหน้าเว็บ (แบ่งตาม State) 🟢
# ==========================================

# ส่วนหัวข้อ (แสดงทุกหน้า)
c_logo, c_title, c_btn = st.columns([1, 6, 2])

with c_logo:
    try:
        st.image("logo.png", width=90) # แก้ชื่อไฟล์ให้ตรงกับที่มี
    except:
        st.write("🏍️") # ถ้าหารูปไม่เจอใส่ emoji แทน

with c_title:
    st.title("ระบบลงทะเบียนรถจักรยานยนต์")
    st.caption("โรงเรียนโพนทองพัฒนาวิทยา")

with c_btn:
    # ปุ่มสลับหน้า อยู่มุมขวาบน
    if st.session_state['page'] == 'student':
        st.button("🔒 สำหรับเจ้าหน้าที่", on_click=go_to_teacher, use_container_width=True)
    else:
        st.button("🏠 กลับหน้าหลัก", on_click=go_to_student, use_container_width=True)

st.markdown("---")

# ---------------------------------------
# 📝 หน้านักเรียนลงทะเบียน
# ---------------------------------------
if st.session_state['page'] == 'student':
    st.info("📝 กรุณากรอกข้อมูลและแนบรูปรถ")
    
    with st.form("reg_form"):
        # --- ส่วนกรอกข้อมูล ---
        c1, c2 = st.columns(2)
        
        with c1:
            sub_c1, sub_c2 = st.columns([1.2, 2]) 
            prefix = sub_c1.selectbox("คำนำหน้า", ["นาย", "นางสาว", "เด็กชาย", "เด็กหญิง", "นาง", "ว่าที่ร้อยตรี", "ครู", "อื่นๆ"])
            if prefix == "อื่นๆ":
                prefix = sub_c1.text_input("ระบุคำนำหน้า", key="other_prefix")
            fname = sub_c2.text_input("ชื่อ-นามสกุล (ไม่ต้องใส่คำนำหน้า)")
            name = f"{prefix}{fname}" if fname else ""

        std_id = c2.text_input("รหัสนักเรียน (บุคคลภายนอกใช้วันเดือนปีเกิด เช่น 020923)")
        
        c3, c4 = st.columns(2)
        level = c3.selectbox("ชั้น", ["ม.1","ม.2","ม.3","ม.4","ม.5","ม.6","บุคลากร","พ่อค้าแม่ค้า"])
        room = c4.text_input("ห้อง")
        
        st.markdown("---")
        
        c5, c6 = st.columns(2)
        brand = c5.selectbox("ยี่ห้อ", ["Honda","Yamaha","Suzuki","GPX","Vespa","อื่นๆ"])
        color = c6.text_input("สีรถ")
        
        plate = st.text_input("ทะเบียน พร้อมจังหวัด (ตัวอย่าง กก1234 ร้อยเอ็ด)")
        
        st.markdown("##### 📄 ข้อมูลเอกสาร")
        doc_col1, doc_col2 = st.columns(2)
        license_status = doc_col1.radio("ใบขับขี่", ["✅ มีใบขับขี่", "❌ ไม่มี"], horizontal=True)
        tax_status = doc_col2.radio("พรบ. และ ภาษี", ["✅ ต่อครบถ้วน", "❌ ขาด/ไม่แน่ใจ"], horizontal=True)
        
        st.markdown("### 📸 ถ่ายรูปรถ (2 มุม)")
        col_img1, col_img2 = st.columns(2)
        photo1 = col_img1.file_uploader("1. รูปด้านหน้า (เห็นทะเบียน)", type=['jpg','png','jpeg'], key="p1")
        photo2 = col_img2.file_uploader("2. รูปด้านข้าง/เต็มคัน", type=['jpg','png','jpeg'], key="p2")
        
        if st.form_submit_button("ส่งข้อมูล", use_container_width=True):
            if fname and std_id and plate and photo1:
                try:
                    sheet = connect_gsheet()
                    existing_ids = sheet.col_values(3) 
                    
                    if std_id in existing_ids:
                        st.error(f"⚠️ รหัสนักเรียน '{std_id}' นี้สมัครไปแล้ว
