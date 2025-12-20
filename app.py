import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import requests  # ใช้ส่งข้อมูลไป Apps Script
import base64    # ใช้แปลงไฟล์รูป

# --- ตั้งค่า (Config) ---
SHEET_NAME = "Motorcycle_DB"
DRIVE_FOLDER_ID = "1WQGATGaGBoIjf44Yj_-DjuX8LZ8kbmBA" 
ADMIN_PASSWORD = "Patwit064180"

# 🔴🔴 เอา URL จาก Google Apps Script (Web App) มาใส่ตรงนี้ 🔴🔴
# URL จะหน้าตาประมาณ: https://script.google.com/macros/s/AKfycbx.../exec
GAS_APP_URL = "https://script.google.com/home/projects/1-biJGY6pZ0ecdYetrsR1iDiAXprRzEJ18TmjGyhe4CdAfko6E0MSDv-w/edit" 

# --- เชื่อมต่อ Google Sheets ---
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

# --- ฟังก์ชันอัปโหลดแบบใหม่ (ส่งไปให้ Apps Script ช่วย) ---
def upload_to_drive(file_obj, filename):
    if GAS_APP_URL == "วาง_URL_ของคุณที่ได้จากขั้นตอน_Deploy_ตรงนี้":
        st.error("🚨 กรุณาใส่ URL ของ Web App ในโค้ดบรรทัดที่ 16 ก่อนครับ")
        return None

    try:
        # อ่านไฟล์และแปลงเป็น Base64
        file_content = file_obj.getvalue()
        base64_str = base64.b64encode(file_content).decode('utf-8')
        
        payload = {
            "folder_id": DRIVE_FOLDER_ID,
            "filename": filename,
            "file": base64_str,
            "mimeType": file_obj.type
        }
        
        # ส่งข้อมูล
        response = requests.post(GAS_APP_URL, json=payload)
        result = response.json()
        
        if result.get("status") == "success":
            return result.get("link")
        else:
            raise Exception(f"Upload failed: {result.get('message')}")
            
    except Exception as e:
        raise Exception(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")

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
        level = c1.selectbox("ชั้น", ["ม.1","ม.2","ม.3","ม.4","ม.5","ม.6","บุคลากร","ผู้ประกอบการ"])
        room = c2.text_input("ห้อง")
        st.markdown("---")
        brand = st.selectbox("ยี่ห้อ", ["Honda","Yamaha","Suzuki","GPX","Vespa","อื่นๆ"])
        plate = st.text_input("ทะเบียน พร้อมจังหวัด(ตัวอย่าง กก1234 ร้อยเอ็ด)")
        color = st.text_input("สีรถ")
        
        st.markdown("### 📸 ถ่ายรูปรถ (2 มุม)")
        col_img1, col_img2 = st.columns(2)
        photo1 = col_img1.file_uploader("1. รูปด้านหน้า (เห็นทะเบียน)", type=['jpg','png','jpeg'], key="p1")
        photo2 = col_img2.file_uploader("2. รูปด้านข้าง/เต็มคัน", type=['jpg','png','jpeg'], key="p2")
        
        if st.form_submit_button("ส่งข้อมูล"):
            if name and plate and photo1: 
                try:
                    with st.spinner("กำลังอัปโหลด..."):
                        clean_plate = plate.replace(" ", "")
                        
                        # อัปโหลดรูปที่ 1
                        link1 = upload_to_drive(photo1, f"{std_id}_{clean_plate}_FRONT.jpg")
                        
                        # อัปโหลดรูปที่ 2 (ถ้ามี)
                        link2 = ""
                        if photo2:
                             link2 = upload_to_drive(photo2, f"{std_id}_{clean_plate}_SIDE.jpg")

                        if link1: # ถ้าอัปโหลดสำเร็จ
                            sheet = connect_gsheet()
                            sheet.append_row([str(datetime.now()), name, std_id, f"{level}/{room}", brand, color, plate, link1, link2])
                            st.success("✅ บันทึกข้อมูลเรียบร้อย!")
                        
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("กรุณากรอกข้อมูลและแนบรูปอย่างน้อย 1 รูป")

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
            
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            st.write(f"พบข้อมูล {len(df)} รายการ")
            
            for i, row in df.iterrows():
                plate_txt = row.get('ทะเบียน', list(row.values())[6]) 
                name_txt = row.get('ชื่อ-นามสกุล', list(row.values())[1])

                with st.expander(f"{plate_txt} : {name_txt}"):
                    c_img, c_text = st.columns([2,1])
                    
                    with c_img:
                        vals = list(row.values())
                        link1 = str(vals[7]) if len(vals) > 7 else ""
                        link2 = str(vals[8]) if len(vals) > 8 else ""

                        cols = st.columns(2)
                        if link1.startswith('http'):
                            cols[0].image(link1, caption="ด้านหน้า", use_column_width=True)
                        if link2.startswith('http'):
                            cols[1].image(link2, caption="ด้านข้าง", use_column_width=True)
                            
                    with c_text:
                        st.write(f"**ชั้น:** {row.get('ชั้น', vals[3])}")
                        st.write(f"**ยี่ห้อ:** {row.get('ยี่ห้อ', vals[4])}")
                        st.write(f"**สี:** {row.get('สี', vals[5])}")
                        st.write(f"**เวลา:** {row.get('Timestamp', vals[0])}")
