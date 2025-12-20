import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import json

# --- ตั้งค่า (Config) ---
SHEET_NAME = "Motorcycle_DB"
# 🔴🔴 แก้ตรงนี้: เอา ID โฟลเดอร์จากด่านที่ 1 มาใส่ 🔴🔴
DRIVE_FOLDER_ID = "1xxxxxxxxxxxxxxxxxxxxxxxxx" 
ADMIN_PASSWORD = "Patwit064180"

# --- เชื่อมต่อ Google ---
def get_creds():
    # ดึงกุญแจจากระบบ Secrets ของ Streamlit (ปลอดภัยกว่าวางไฟล์)
    key_dict = json.loads(st.secrets["textkey"]["json_content"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)

def connect_gsheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def upload_to_drive(file_obj, filename):
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
    media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- หน้าเว็บ ---
st.set_page_config(page_title="ทะเบียนรถ รร.", page_icon="🛵")
st.title("🛵 ระบบลงทะเบียนรถจักรยานยนต์โรงเรียนโพนทองพัฒนาวิทยา")

menu = st.sidebar.radio("เมนู", ["📝 นักเรียนลงทะเบียน", "👮 ครูตรวจสอบ"])

if menu == "📝 นักเรียนลงทะเบียน":
    st.info("กรุณากรอกข้อมูลและแนบรูปรถ")
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("ชื่อ-นามสกุล")
        std_id = c2.text_input("รหัสนักเรียน")
        level = c1.selectbox("ชั้น", ["ม.1","ม.2","ม.3","ม.4","ม.5","ม.6",])
        room = c2.text_input("ห้อง")
        st.markdown("---")
        brand = st.selectbox("ยี่ห้อ", ["Honda","Yamaha","Suzuki","GPX","Vespa","อื่นๆ"])
        plate = st.text_input("ทะเบียน (พร้อมจังหวัด)")
        color = st.text_input("สีรถ")
        st.markdown("### 📸 ถ่ายรูปรถ")
        photo = st.file_uploader("เลือกรูป", type=['jpg','png','jpeg'])
        
        if st.form_submit_button("ส่งข้อมูล"):
            if name and plate and photo:
                try:
                    with st.spinner("กำลังอัปโหลด..."):
                        link = upload_to_drive(photo, f"{std_id}_{plate}.jpg")
                        sheet = connect_gsheet()
                        sheet.append_row([str(datetime.now()), name, std_id, f"{level}/{room}", brand, color, plate, link])
                    st.success("✅ เรียบร้อย!")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("กรอกให้ครบทุกช่องนะครับ")

elif menu == "👮 ครูตรวจสอบ":
    pwd = st.text_input("รหัสผ่านเจ้าหน้าที่", type="password")
    if pwd == ADMIN_PASSWORD:
        if st.button("โหลดข้อมูล"):
            try:
                data = connect_gsheet().get_all_records()
                st.session_state['df'] = pd.DataFrame(data)
            except: st.error("ไม่พบข้อมูล")
        
        if 'df' in st.session_state:
            search = st.text_input("🔍 ค้นหา (ชื่อ/ทะเบียน)")
            df = st.session_state['df']
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            for i, row in df.iterrows():
                with st.expander(f"{row['ทะเบียน']} - {row['ชื่อ-นามสกุล']}"):
                    st.write(f"ชั้น: {row['ชั้น']} | รถ: {row['ยี่ห้อ']} ({row['สี']})")
                    if str(row['รูปภาพ']).startswith('http'):
                        st.image(row['รูปภาพ'])
                    else: st.write("ไม่มีรูป")
