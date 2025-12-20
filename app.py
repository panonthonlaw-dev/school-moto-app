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
# 🔴🔴 (สำคัญ) อย่าลืมใส่ ID โฟลเดอร์รูปภาพของครูตรงนี้นะครับ 🔴🔴
DRIVE_FOLDER_ID = "1WQGATGaGBoIjf44Yj_-DjuX8LZ8kbmBA" 
ADMIN_PASSWORD = "Patwit064180"

# --- เชื่อมต่อ Google ---
def get_creds():
    # 🔧 แก้ไขจุดที่ Error: เพิ่ม strict=False เพื่อให้โปรแกรมไม่งอแงเรื่องตัวอักษร
    key_content = st.secrets["textkey"]["json_content"]
    # ป้องกันปัญหาเรื่องตัวเว้นบรรทัด (Newlines) ที่มักจะ Error
    try:
        key_dict = json.loads(key_content, strict=False)
    except json.JSONDecodeError:
        # ถ้ายัง Error ให้ลองล้างค่าตัวอักษรพิเศษ
        clean_content = key_content.replace('\n', '\\n')
        key_dict = json.loads(clean_content, strict=False)
        
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
st.title("🛵 ระบบลงทะเบียนรถจักรยานยนต์พัฒวิทย์")

# สร้างเมนู
menu = st.sidebar.radio("เมนู", ["📝 นักเรียนลงทะเบียน", "👮 ครูตรวจสอบ"])

if menu == "📝 นักเรียนลงทะเบียน":
    st.info("กรุณากรอกข้อมูลและแนบรูปรถ")
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("ชื่อ-นามสกุล")
        std_id = c2.text_input("รหัสนักเรียน")
        level = c1.selectbox("ชั้น", ["ม.1","ม.2","ม.3","ม.4","ม.5","ม.6","คุณครู","ผู้ประกอบการ"])
        room = c2.text_input("ห้อง")
        st.markdown("---")
        brand = st.selectbox("ยี่ห้อ", ["Honda","Yamaha","Suzuki","GPX","Vespa","อื่นๆ"])
        plate = st.text_input("ทะเบียน พร้อมจังหวัด(ตัวอย่าง กก1234 ร้อยเอ็ด)")
        color = st.text_input("สีรถ")
        st.markdown("### 📸 ถ่ายรูปรถ")
        photo = st.file_uploader("เลือกรูป", type=['jpg','png','jpeg'])
        
        if st.form_submit_button("ส่งข้อมูล"):
            if name and plate and photo:
                try:
                    with st.spinner("กำลังอัปโหลด..."):
                        # สร้างชื่อไฟล์ไม่ให้ซ้ำ
                        clean_plate = plate.replace(" ", "")
                        file_name = f"{std_id}_{clean_plate}.jpg"
                        
                        link = upload_to_drive(photo, file_name)
                        sheet = connect_gsheet()
                        sheet.append_row([str(datetime.now()), name, std_id, f"{level}/{room}", brand, color, plate, link])
                    st.success("✅ บันทึกข้อมูลเรียบร้อย!")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("กรุณากรอกข้อมูลให้ครบทุกช่อง")

elif menu == "👮 ครูตรวจสอบ":
    pwd = st.text_input("รหัสผ่านเจ้าหน้าที่", type="password")
    if pwd == ADMIN_PASSWORD:
        if st.button("โหลดข้อมูลล่าสุด"):
            try:
                data = connect_gsheet().get_all_records()
                if data:
                    st.session_state['df'] = pd.DataFrame(data)
                else:
                    st.warning("ยังไม่มีข้อมูลในระบบ")
            except Exception as e: 
                st.error(f"ดึงข้อมูลไม่ได้: {e}")
        
        if 'df' in st.session_state:
            search = st.text_input("🔍 ค้นหา (ชื่อ/ทะเบียน)")
            df = st.session_state['df']
            
            # กรองข้อมูล
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            st.write(f"พบข้อมูล {len(df)} รายการ")
            
            for i, row in df.iterrows():
                with st.expander(f"{row.get('ทะเบียน','-')} : {row.get('ชื่อ-นามสกุล','-')}"):
                    c_img, c_text = st.columns([1,2])
                    with c_img:
                        if str(row.get('รูปภาพ','')).startswith('http'):
                            st.image(row['รูปภาพ'], use_column_width=True)
                        else: st.write("ไม่มีรูป")
                    with c_text:
                        st.write(f"**ชั้น:** {row.get('ชั้น','-')}")
                        st.write(f"**รถ:** {row.get('ยี่ห้อ','-')} สี {row.get('สี','-')}")
                        st.write(f"**วันเวลา:** {row.get('Timestamp','-')}")
