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
                data = connect_gsheet().get_all_records()
                if data:
                    st.session_state['df'] = pd.DataFrame(data)
                else:
                    st.warning("ยังไม่มีข้อมูลในระบบ")
            except Exception as e: 
                st.error(f"ดึงข้อมูลไม่ได้: {e}")
        
        if 'df' in st.session_state:
            search = st.text_input("🔍 ค้นหา (ชื่อ/ทะเบียน/ชั้น)")
            df = st.session_state['df']
            
            if search:
                # แก้ไขการค้นหาให้ครอบคลุมทุกคอลัมน์ (แปลงเป็น string ก่อนค้นหา)
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            st.write(f"พบข้อมูล {len(df)} รายการ")
            
            # --- ฟังก์ชันดึงรูป (เหมือนเดิม) ---
            def get_reliable_image_url(url):
                url = str(url).strip()
                if not url or url == "": return None
                import re
                file_id = None
                patterns = [r'/d/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)']
                for p in patterns:
                    match = re.search(p, url)
                    if match:
                        file_id = match.group(1)
                        break
                if file_id:
                    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"
                return url

            # วนลูปแสดงผล
            for i, row in df.iterrows():
                plate_txt = row.get('ทะเบียน', '-')
                name_txt = row.get('ชื่อ-นามสกุล', '-')

                # แสดงหัวข้อ Expander
                with st.expander(f"🛵 {plate_txt} | 👤 {name_txt}"):
                    c_img, c_text = st.columns([2,1])
                    
                    with c_img:
                        vals = row.tolist() 
                        # ดึงลิงก์ (ช่องรองสุดท้าย และ ช่องสุดท้าย)
                        raw_link1 = str(vals[-2]).strip() if len(vals) >= 2 else ""
                        raw_link2 = str(vals[-1]).strip() if len(vals) >= 1 else ""

                        img_url1 = get_reliable_image_url(raw_link1)
                        img_url2 = get_reliable_image_url(raw_link2)

                        cols = st.columns(2)
                        if img_url1:
                            cols[0].image(img_url1, caption="ด้านหน้า", use_column_width=True)
                        else:
                            cols[0].info("ไม่มีรูป")

                        if img_url2:
                            cols[1].image(img_url2, caption="ด้านข้าง", use_column_width=True)
                        
                    with c_text:
                        # --- 🔴 ส่วนที่เพิ่ม: แสดงชื่อเจ้าของรถชัดๆ ---
                        st.markdown(f"### 👤 {name_txt}")
                        st.write(f"**รหัสนักเรียน:** {row.get('รหัสนักเรียน', '-')}")
                        st.markdown("---")
                        # ----------------------------------------
                        
                        st.write(f"**ทะเบียน:** {plate_txt}")
                        st.write(f"**ชั้น:** {row.get('ชั้น', '-')}")
                        st.write(f"**ยี่ห้อ:** {row.get('ยี่ห้อ', '-')}")
                        st.write(f"**สี:** {row.get('สี', '-')}")
                        
                        st.markdown("---")
                        
                        # สถานะเอกสาร (ใส่สีให้ดูง่าย)
                        lic = row.get('ใบขับขี่', '-')
                        tax = row.get('พรบ_ภาษี', '-')
                        
                        if "มี" in str(lic): st.success(f"ใบขับขี่: {lic}")
                        else: st.error(f"ใบขับขี่: {lic}")
                            
                        if "ครบ" in str(tax): st.success(f"พรบ./ภาษี: {tax}")
                        else: st.error(f"พรบ./ภาษี: {tax}")
                        
                        # ปุ่ม Debug
                        with st.expander("🔧 Link ต้นฉบับ"):
                            st.code(f"Link1: {raw_link1}\nLink2: {raw_link2}")
