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
# ตรงนี้ใส่ชื่อไฟล์โลโก้ของคุณ (ควรมีนามสกุลไฟล์ด้วย เช่น .png, .jpg)
st.set_page_config(page_title="patwit moto.", page_icon="logo")
# 🟢🟢 แทรกโค้ด CSS ตรงนี้ เพื่อซ่อนปุ่ม GitHub/Deploy แต่เก็บลูกศรไว้ 🟢🟢
st.markdown("""
    <style>
        /* ซ่อนปุ่ม Deploy (ปุ่ม GitHub) */
        .stDeployButton {
            visibility: hidden;
        }
        /* ซ่อนเมนู 3 จุด ด้านขวาบน (ถ้าต้องการเอาออกด้วย) */
        [data-testid="stToolbar"] {
            visibility: hidden;
        }
        /* ซ่อนขีดสีรุ้งด้านบนสุดของจอ */
        [data-testid="stDecoration"] {
            display: none;
        }
        /* ซ่อน Footer (Made with Streamlit) */
        footer {
            visibility: hidden;
        }
    </style>
""", unsafe_allow_html=True)
# --- ส่วนหัวข้อแบบมีโลโก้ (แก้ใหม่ตรงนี้) ---
# แบ่งเป็น 2 คอลัมน์: [ช่องเล็กสำหรับรูป, ช่องใหญ่สำหรับข้อความ]
c_logo, c_title = st.columns([1, 6]) # ลองปรับเลข 1 กับ 6 เพื่อเปลี่ยนสัดส่วนความกว้าง

with c_logo:
    # แสดงรูปโลโก้ (ปรับขนาด width ตามต้องการ)
    st.image("logo", width=90) 

with c_title:
    # แสดงข้อความหัวข้อ (ไม่ต้องมีอิโมจิ 🛵 แล้ว)
    st.title("ระบบลงทะเบียนรถจักรยานยนต์โรงเรียนโพนทองพัฒนาวิทยา")
# ---------------------------------------

menu = st.sidebar.radio("เมนู", ["📝 นักเรียนลงทะเบียน", "👮 ครูตรวจสอบ"])

if menu == "📝 นักเรียนลงทะเบียน":
    st.info("กรุณากรอกข้อมูลและแนบรูปรถ")
    with st.form("reg_form"):
        # --- ส่วนกรอกข้อมูล (เหมือนเดิม) ---
        c1, c2 = st.columns(2)
        
        with c1:
            sub_c1, sub_c2 = st.columns([1.2, 2]) 
            prefix = sub_c1.selectbox("คำนำหน้า", ["นาย", "นางสาว", "เด็กชาย", "เด็กหญิง", "นาง", "ว่าที่ร้อยตรี", "ครู", "อื่นๆ"])
            if prefix == "อื่นๆ":
                prefix = sub_c1.text_input("ระบุคำนำหน้า", key="other_prefix")
            fname = sub_c2.text_input("ชื่อ-นามสกุล (ไม่ต้องใส่คำนำหน้า)")
            name = f"{prefix}{fname}" if fname else ""

        std_id = c2.text_input("รหัสนักเรียน หากเป็นบุคลากร,พ่อค้าแม่ค้าใช้วันเดือนปีเกิด เช่น2 กันยายน 2523 ใส่020923")
        
        c3, c4 = st.columns(2)
        level = c3.selectbox("ชั้น", ["ม.1","ม.2","ม.3","ม.4","ม.5","ม.6","บุคลากร","พ่อค้าแม่ค้า"])
        room = c4.text_input("ห้อง")
        
        st.markdown("---")
        
        c5, c6 = st.columns(2)
        brand = c5.selectbox("ยี่ห้อ", ["Honda","Yamaha","Suzuki","GPX","Vespa","อื่นๆ"])
        color = c6.text_input("สีรถ")
        
        plate = st.text_input("ทะเบียน พร้อมจังหวัด(ตัวอย่าง กก1234 ร้อยเอ็ด)")
        
        st.markdown("##### 📄 ข้อมูลเอกสาร")
        doc_col1, doc_col2 = st.columns(2)
        license_status = doc_col1.radio("ใบขับขี่", ["✅ มีใบขับขี่", "❌ ไม่มี"], horizontal=True)
        tax_status = doc_col2.radio("พรบ. และ ภาษี", ["✅ ต่อครบถ้วน", "❌ ขาด/ไม่แน่ใจ"], horizontal=True)
        
        st.markdown("### 📸 ถ่ายรูปรถ (2 มุม)")
        col_img1, col_img2 = st.columns(2)
        photo1 = col_img1.file_uploader("1. รูปด้านหน้า (เห็นทะเบียน)", type=['jpg','png','jpeg'], key="p1")
        photo2 = col_img2.file_uploader("2. รูปด้านข้าง/เต็มคัน", type=['jpg','png','jpeg'], key="p2")
        
        if st.form_submit_button("ส่งข้อมูล"):
            if fname and std_id and plate and photo1: # เช็ค std_id ด้วยว่ากรอกไหม
                try:
                    # 🔴🔴 1. เช็คก่อนว่ามีรหัสนักเรียนซ้ำไหม 🔴🔴
                    sheet = connect_gsheet()
                    # ดึงข้อมูลชื่อ-สกุลทั้งหมด (คอลัมน์ที่ 3) มาตรวจสอบ
                    existing_ids = sheet.col_values(3) 
                    
                    if std_id in existing_ids:
                        # ถ้าเจอซ้ำ ให้แจ้งเตือนและหยุดทำงานทันที
                        st.error(f"⚠️ รหัสนักเรียน '{std_id}' นี้สมัครไปแล้ว!")
                        st.warning("หากต้องการแก้ไขข้อมูล กรุณาติดต่อ **'ตำรวจนักเรียน'**")
                    
                    else:
                        # 🟢🔴 2. ถ้าไม่ซ้ำ ค่อยทำขั้นตอนอัปโหลดและบันทึก 🔴🟢
                        with st.spinner("กำลังอัปโหลด..."):
                            clean_plate = plate.replace(" ", "")
                            
                            link1 = upload_to_drive(photo1, f"{std_id}_{clean_plate}_FRONT.jpg")
                            
                            link2 = ""
                            if photo2:
                                 link2 = upload_to_drive(photo2, f"{std_id}_{clean_plate}_SIDE.jpg")

                            if link1: 
                                sheet.append_row([
                                    str(datetime.now()), 
                                    name, 
                                    std_id, 
                                    f"{level}/{room}", 
                                    brand, 
                                    color, 
                                    plate,
                                    license_status,
                                    tax_status,
                                    link1, 
                                    link2
                                ])
                                st.success(f"✅ บันทึกข้อมูล {name} เรียบร้อย!")
                        
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("กรุณากรอกข้อมูลให้ครบ (ชื่อ, รหัสนักเรียน, ทะเบียน, รูปภาพ)")

elif menu == "👮 ครูตรวจสอบ":
    st.markdown("### 👮 ส่วนสำหรับเจ้าหน้าที่")
    pwd = st.text_input("กรอกรหัสผ่านเพื่อเข้าถึงข้อมูล", type="password")
    
    # --- เช็คความถูกต้องของรหัสผ่าน (ชั้นที่ 1) ---
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
            df = st.session_state['df']
            
            # --- 📊 ส่วน Dashboard ---
            st.markdown("### 📊 สรุปภาพรวม")
            total_cars = len(df)
            
            try:
                has_license = df[df.iloc[:, 7].astype(str).str.contains("มี", na=False)].shape[0]
                has_tax = df[df.iloc[:, 8].astype(str).str.contains("ครบ|ปกติ", na=False)].shape[0]
            except:
                has_license = 0
                has_tax = 0

            m1, m2, m3 = st.columns(3)
            m1.metric("🏍️ ทั้งหมด", f"{total_cars} คัน")
            m2.metric("🪪 มีใบขับขี่", f"{has_license} คน", f"{(has_license/total_cars*100):.1f}%" if total_cars else "0%")
            m3.metric("📝 พรบ./ภาษี", f"{has_tax} คัน", f"{(has_tax/total_cars*100):.1f}%" if total_cars else "0%")
            
            st.markdown("---")
            
            # --- ส่วนค้นหา ---
            search = st.text_input("🔍 ค้นหา (ชื่อ/ทะเบียน)")
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            st.write(f"พบข้อมูล {len(df)} รายการ")
            
            # ฟังก์ชันแก้ลิงก์รูป
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

            # --- วนลูปแสดงข้อมูล ---
            for i, row in df.iterrows():
                vals = row.tolist()
                
                name_txt = str(vals[1]) if len(vals) > 1 else "-"
                std_id_txt = str(vals[2]) if len(vals) > 2 else "-"
                level_txt = str(vals[3]) if len(vals) > 3 else "-"
                brand_txt = str(vals[4]) if len(vals) > 4 else "-"
                color_txt = str(vals[5]) if len(vals) > 5 else "-"
                plate_txt = str(vals[6]) if len(vals) > 6 else "-"
                
                raw_link1 = str(vals[-2]).strip() if len(vals) >= 2 else ""
                raw_link2 = str(vals[-1]).strip() if len(vals) >= 1 else ""

                img_url1 = get_reliable_image_url(raw_link1)
                img_url2 = get_reliable_image_url(raw_link2)

                with st.expander(f"🛵 {plate_txt} | 👤 {name_txt}"):
                    c_img, c_text = st.columns([2,1])
                    
                    with c_img:
                        cols = st.columns(2)
                        if img_url1: cols[0].image(img_url1, caption="ด้านหน้า", use_column_width=True)
                        else: cols[0].info("ไม่มีรูป")

                        if img_url2: cols[1].image(img_url2, caption="ด้านข้าง", use_column_width=True)
                        
                    with c_text:
                        st.markdown(f"### 👤 {name_txt}")
                        st.write(f"**รหัส:** {std_id_txt}")
                        st.markdown("---")
                        st.write(f"**ทะเบียน:** {plate_txt}")
                        st.write(f"**ชั้น:** {level_txt}")
                        st.write(f"**ยี่ห้อ:** {brand_txt}")
                        st.write(f"**สี:** {color_txt}")
                        st.markdown("---")
                        
                        lic = str(vals[7]) if len(vals) > 7 else "-"
                        tax = str(vals[8]) if len(vals) > 8 else "-"
                        
                        if "http" in lic: lic = row.get('ใบขับขี่', '-')
                        if "http" in tax: tax = row.get('พรบ_ภาษี', '-')

                        if "มี" in str(lic): st.success(f"ใบขับขี่: {lic}")
                        else: st.error(f"ใบขับขี่: {lic}")
                            
                        if "ครบ" in str(tax) or "ปกติ" in str(tax): st.success(f"พรบ./ภาษี: {tax}")
                        else: st.error(f"พรบ./ภาษี: {tax}")
                        
                        with st.expander("🔧 Link ต้นฉบับ"):
                             st.code(f"Link1: {raw_link1}\nLink2: {raw_link2}")
            
            # =========================================================
            # ⚙️ ส่วนระบบเลื่อนชั้นปี (มีรหัสป้องกัน 2 ชั้น)
            # =========================================================
            st.markdown("---")
            with st.expander("⚙️ จัดการเลื่อนชั้นปี (สำหรับสิ้นปีการศึกษา)"):
                st.warning("⚠️ โซนอันตราย: การดำเนินการนี้จะแก้ไขข้อมูลทั้งหมดในฐานข้อมูล")
                
                # ช่องใส่รหัสลับชั้นที่ 2
                super_pwd = st.text_input("🔑 กรุณาใส่รหัสลับ (Super Admin) เพื่อยืนยัน", type="password")
                
                if st.button("🚀 ยืนยันเลื่อนชั้นเรียนทั้งหมด"):
                    # 🔴🔴 กำหนดรหัสสำหรับการเลื่อนชั้น ตรงนี้ครับ 🔴🔴
                    PROMOTION_SECRET_KEY = "Patwitnext" 
                    
                    if super_pwd == PROMOTION_SECRET_KEY:
                        try:
                            sheet = connect_gsheet()
                            all_data = sheet.get_all_values()
                            header = all_data[0]
                            rows = all_data[1:]
                            
                            level_idx = 3 
                            for idx, h in enumerate(header):
                                if "ชั้น" in h:
                                    level_idx = idx
                                    break
                            
                            updated_rows = []
                            change_count = 0
                            
                            for row in rows:
                                if len(row) > level_idx:
                                    old_level = row[level_idx]
                                    new_level = old_level
                                    
                                    if "ม.1" in old_level: new_level = old_level.replace("ม.1", "ม.2")
                                    elif "ม.2" in old_level: new_level = old_level.replace("ม.2", "ม.3")
                                    elif "ม.3" in old_level: new_level = "จบการศึกษา 🎓"
                                    elif "ม.4" in old_level: new_level = old_level.replace("ม.4", "ม.5")
                                    elif "ม.5" in old_level: new_level = old_level.replace("ม.5", "ม.6")
                                    elif "ม.6" in old_level: new_level = "จบการศึกษา 🎓"
                                    
                                    if old_level != new_level:
                                        row[level_idx] = new_level
                                        change_count += 1
                                        
                                updated_rows.append(row)
                            
                            if change_count > 0:
                                sheet.clear()
                                sheet.update('A1', [header] + updated_rows)
                                st.success(f"✅ เลื่อนชั้นสำเร็จ {change_count} คน! (รีเฟรชเพื่อดูข้อมูลใหม่)")
                                st.balloons()
                            else:
                                st.info("ไม่มีข้อมูลต้องเลื่อนชั้น")
                                
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาด: {e}")
                    else:
                        st.error("❌ รหัสลับไม่ถูกต้อง! การเลื่อนชั้นถูกยกเลิก")

    elif pwd != "": 
        st.error("❌ รหัสผ่านไม่ถูกต้อง! กรุณาตรวจสอบอีกครั้ง")
