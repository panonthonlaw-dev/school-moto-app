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

# 🔴🔴 อย่าลืมเอา URL ของ Google Apps Script มาใส่ตรงนี้เหมือนเดิมนะครับ 🔴🔴
GAS_APP_URL = "https://script.google.com/macros/s/AKfycbxRf6z032SxMkiI4IxtUBvWLKeo1LmIQAUMByoXidy4crNEwHoO6h0B-3hT0X7Q5g/exec" 

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

# --- ฟังก์ชันอัปโหลด ---
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

# --- หน้าเว็บ ---
st.set_page_config(page_title="ทะเบียนรถ รร.", page_icon="🛵")
st.title("🛵 ระบบลงทะเบียนรถจักรยานยนต์พัฒวิทย์")

menu = st.sidebar.radio("เมนู", ["📝 นักเรียนลงทะเบียน", "👮 ครูตรวจสอบ"])

if menu == "📝 นักเรียนลงทะเบียน":
    st.info("กรุณากรอกข้อมูลและแนบรูปรถ")
    with st.form("reg_form"):
        # แถว 1
        c1, c2 = st.columns(2)
        name = c1.text_input("ชื่อ-นามสกุล")
        std_id = c2.text_input("รหัสนักเรียน")
        
        # แถว 2
        c3, c4 = st.columns(2)
        level = c3.selectbox("ชั้น", ["ม.1","ม.2","ม.3","ม.4","ม.5","ม.6","บุคลากร","ผู้ประกอบการ"])
        room = c4.text_input("ห้อง")
        
        st.markdown("---")
        
        # แถว 3
        c5, c6 = st.columns(2)
        brand = c5.selectbox("ยี่ห้อ", ["Honda","Yamaha","Suzuki","GPX","Vespa","อื่นๆ"])
        color = c6.text_input("สีรถ")
        
        plate = st.text_input("ทะเบียน พร้อมจังหวัด(ตัวอย่าง กก1234 ร้อยเอ็ด)")
        
        # --- (ส่วนที่เพิ่มใหม่) ---
        st.markdown("##### 📄 ข้อมูลเอกสาร")
        doc_col1, doc_col2 = st.columns(2)
        license_status = doc_col1.radio("ใบขับขี่", ["✅ มีใบขับขี่", "❌ ไม่มี"], horizontal=True)
        tax_status = doc_col2.radio("พรบ. และ ภาษี", ["✅ ต่อครบถ้วน", "❌ ขาด/ไม่แน่ใจ"], horizontal=True)
        # ------------------------
        
        st.markdown("### 📸 ถ่ายรูปรถ (2 มุม)")
        col_img1, col_img2 = st.columns(2)
        photo1 = col_img1.file_uploader("1. รูปด้านหน้า (เห็นทะเบียน)", type=['jpg','png','jpeg'], key="p1")
        photo2 = col_img2.file_uploader("2. รูปด้านข้าง/เต็มคัน", type=['jpg','png','jpeg'], key="p2")
        
        if st.form_submit_button("ส่งข้อมูล"):
            if name and plate and photo1: 
                try:
                    with st.spinner("กำลังอัปโหลด..."):
                        clean_plate = plate.replace(" ", "")
                        
                        link1 = upload_to_drive(photo1, f"{std_id}_{clean_plate}_FRONT.jpg")
                        
                        link2 = ""
                        if photo2:
                             link2 = upload_to_drive(photo2, f"{std_id}_{clean_plate}_SIDE.jpg")

                        if link1: 
                            sheet = connect_gsheet()
                            # บันทึกข้อมูลเพิ่ม (license_status, tax_status)
                            sheet.append_row([
                                str(datetime.now()), 
                                name, 
                                std_id, 
                                f"{level}/{room}", 
                                brand, 
                                color, 
                                plate,
                                license_status, # เพิ่มตรงนี้
                                tax_status,     # เพิ่มตรงนี้
                                link1, 
                                link2
                            ])
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
                # ดึงข้อมูลใหม่ทั้งหมด
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
            
            # วนลูปแสดงผล
            for i, row in df.iterrows():
                # ใช้ .get เพื่อความปลอดภัย (ถ้าไม่เจอ key จะได้ไม่ error)
                plate_txt = row.get('ทะเบียน', '-')
                name_txt = row.get('ชื่อ-นามสกุล', '-')

                with st.expander(f"{plate_txt} : {name_txt}"):
                    c_img, c_text = st.columns([2,1])
                    
                    with c_img:
                        # --- แก้ไขจุดที่ Error ตรงนี้ครับ ---
                        vals = row.tolist() # เปลี่ยนเป็น tolist()
                        
                        # พยายามดึงลิงก์จากคอลัมน์ท้ายๆ
                        # (เพราะเราเพิ่มคอลัมน์ ใบขับขี่/ภาษี แทรกเข้ามา ลิงก์รูปจะเลื่อนไปอยู่ท้ายสุด)
                        link1 = str(vals[-2]) if len(vals) >= 2 else "" # รองสุดท้าย
                        link2 = str(vals[-1]) if len(vals) >= 1 else "" # สุดท้าย

                        cols = st.columns(2)
                        # ตรวจสอบว่าเป็นลิงก์จริงไหม
                        if "http" in link1:
                            cols[0].image(link1, caption="ด้านหน้า", use_column_width=True)
                        else:
                            cols[0].write("ไม่มีรูป 1")
                            
                        if "http" in link2:
                            cols[1].image(link2, caption="ด้านข้าง", use_column_width=True)
                        else:
                            cols[1].write("ไม่มีรูป 2")
                            
                    with c_text:
                        st.write(f"**ชั้น:** {row.get('ชั้น', '-')}")
                        st.write(f"**ยี่ห้อ:** {row.get('ยี่ห้อ', '-')}")
                        st.write(f"**สี:** {row.get('สีรถ', row.get('สี', '-'))}")
                        
                        st.markdown("---")
                        # ดึงข้อมูลใหม่ที่เพิ่งเพิ่ม
                        st.write(f"**ใบขับขี่:** {row.get('ใบขับขี่', '-')}")
                        st.write(f"**พรบ./ภาษี:** {row.get('พรบ_ภาษี', '-')}")
