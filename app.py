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
        header { visibility: hidden !important; height: 0px !important; }
        footer { visibility: hidden !important; height: 0px !important; }
        [data-testid="stSidebar"] { display: none; }
        .block-container { padding-top: 2rem; }
        .staff-btn-container { margin-top: 50px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- State Management ---
if 'page' not in st.session_state:
    st.session_state['page'] = 'student'

def go_to_teacher():
    st.session_state['page'] = 'teacher'

def go_to_student():
    st.session_state['page'] = 'student'

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
        st.error("🚨 กรุณาใส่ URL Web App")
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
# ส่วนหัวเว็บ
# ==========================================
c_logo, c_title = st.columns([1, 8])
with c_logo:
    try:
        st.image("logo", width=90) 
    except:
        st.write("🏍️") 
with c_title:
    st.title("ระบบลงทะเบียนรถจักรยานยนต์")
    st.caption("โรงเรียนโพนทองพัฒนาวิทยา")
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
            # บรรทัดที่มีปัญหา แก้ไขให้แล้วครับ
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
        
        # ปุ่มส่งข้อมูล
        submitted = st.form_submit_button("ส่งข้อมูล", use_container_width=True)

        if submitted:
            if fname and std_id and plate and photo1:
                try:
                    sheet = connect_gsheet()
                    existing_ids = sheet.col_values(3) 
                    
                    if std_id in existing_ids:
                        st.error(f"⚠️ รหัสนักเรียน '{std_id}' นี้สมัครไปแล้ว!") 
                        st.warning("หากต้องการแก้ไขข้อมูล กรุณาติดต่อ **'ตำรวจนักเรียน'**")
                    else:
                        with st.spinner("กำลังอัปโหลด..."):
                            clean_plate = plate.replace(" ", "")
                            link1 = upload_to_drive(photo1, f"{std_id}_{clean_plate}_FRONT.jpg")
                            link2 = ""
                            if photo2:
                                 link2 = upload_to_drive(photo2, f"{std_id}_{clean_plate}_SIDE.jpg")

                            if link1: 
                                sheet.append_row([str(datetime.now()), name, std_id, f"{level}/{room}", brand, color, plate, license_status, tax_status, link1, link2])
                                st.success(f"✅ บันทึกข้อมูล {name} เรียบร้อย!")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("กรุณากรอกข้อมูลให้ครบ")

    # ปุ่มเจ้าหน้าที่ (อยู่ล่างสุด)
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    c_staff_btn = st.columns([1, 2, 1])
    with c_staff_btn[1]:
        if st.button("🔐 สำหรับเจ้าหน้าที่ / ครู", use_container_width=True):
            go_to_teacher()
            st.rerun()
            # ---------------------------------------
# 👮 หน้าเจ้าหน้าที่ตรวจสอบ (Part 3.1 ปรับปรุง Dashboard)
# ---------------------------------------
elif st.session_state['page'] == 'teacher':
    if st.button("🏠 กลับหน้าลงทะเบียน", on_click=go_to_student):
        st.rerun()
        
    st.markdown("### 👮 ส่วนสำหรับเจ้าหน้าที่")
    
    if 'logged_in' not in st.session_state: 
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        pwd = st.text_input("กรอกรหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if st.button("🚪 ออกจากระบบ"):
            st.session_state['logged_in'] = False
            st.rerun()
        
        st.success("เข้าสู่ระบบเรียบร้อย")
        if st.button("🔄 โหลดข้อมูลล่าสุด"):
            try:
                data = connect_gsheet().get_all_records()
                if data: 
                    st.session_state['df'] = pd.DataFrame(data)
                else: 
                    st.warning("ยังไม่มีข้อมูล")
            except Exception as e: 
                st.error(f"ดึงข้อมูลไม่ได้: {e}")
        
        if 'df' in st.session_state:
            df = st.session_state['df']
            st.markdown("### 📊 สรุปภาพรวม")
            
            # คำนวณตัวเลข
            total = len(df)
            try:
                # นับจำนวนคนที่มีใบขับขี่ และ ภาษีครบ
                lic = df[df.iloc[:, 7].astype(str).str.contains("มี", na=False)].shape[0]
                tax = df[df.iloc[:, 8].astype(str).str.contains("ครบ|ปกติ", na=False)].shape[0]
                
                # คำนวณเปอร์เซ็นต์ (ป้องกันการหารด้วย 0)
                if total > 0:
                    lic_pct = (lic / total) * 100
                    tax_pct = (tax / total) * 100
                else:
                    lic_pct = 0
                    tax_pct = 0
            except: 
                lic=0; tax=0; lic_pct=0; tax_pct=0

            # แสดงผลแบบ 3 คอลัมน์ พร้อมเปอร์เซ็นต์
            c1, c2, c3 = st.columns(3)
            c1.metric("🏍️ รถทั้งหมด", f"{total} คัน")
            c2.metric("🪪 มีใบขับขี่", f"{lic} คน ({lic_pct:.1f}%)")
            c3.metric("📝 พรบ./ภาษี", f"{tax} คัน ({tax_pct:.1f}%)")
            
            st.markdown("---")
            # (Part 3.2 ต่อจากด้านบน)
            search = st.text_input("🔍 ค้นหา (ชื่อ/ทะเบียน)")
            if search: 
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            st.write(f"พบข้อมูล {len(df)} รายการ")
            
            def get_img(url):
                url = str(url).strip()
                if not url: return None
                import re
                file_id = None
                match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
                if match: file_id = match.group(1)
                else: 
                    match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
                    if match: file_id = match.group(1)
                if file_id: 
                    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"
                return url

            for i, row in df.iterrows():
                vals = row.tolist()
                name_t = str(vals[1]) if len(vals)>1 else "-"
                plate_t = str(vals[6]) if len(vals)>6 else "-"
                img1 = get_img(str(vals[-2])) if len(vals)>=2 else None
                img2 = get_img(str(vals[-1])) if len(vals)>=1 else None
                
                with st.expander(f"🛵 {plate_t} | {name_t}"):
                    ci, ct = st.columns([2,1])
                    with ci:
                        cc = st.columns(2)
                        if img1: cc[0].image(img1, caption="หน้า")
                        if img2: cc[1].image(img2, caption="ข้าง")
                    with ct:
                        st.write(f"**ชื่อ:** {name_t}")
                        st.write(f"**รหัส:** {str(vals[2]) if len(vals)>2 else '-'}")
                        st.write(f"**ทะเบียน:** {plate_t}")
                        st.write(f"**ชั้น:** {str(vals[3]) if len(vals)>3 else '-'}")
                        # บรรทัดที่เคยมีปัญหา คือบรรทัดนี้ครับ
                        st.write(f"**รุ่น/สี:** {str(vals[4])} {str(vals[5])}")

            st.markdown("---")
            with st.expander("⚙️ เลื่อนชั้นปี (สำหรับสิ้นปีการศึกษา)"):
                st.error("⚠️ คำเตือน: ข้อมูลชั้นเรียนเก่าจะถูกเปลี่ยนและไม่สามารถกู้คืนย้อนหลังได้")
                
                spwd = st.text_input("รหัสลับ (Super Admin)", type="password")
                
                if st.button("ยืนยันเลื่อนชั้น"):
                    if spwd == "Patwitnext":
                        try:
                            sheet = connect_gsheet()
                            d = sheet.get_all_values()
                            h = d[0]; r = d[1:]
                            l_idx = 3
                            for i,x in enumerate(h): 
                                if "ชั้น" in x: l_idx=i; break
                            
                            new_r = []
                            chg = 0
                            for row in r:
                                if len(row) > l_idx:
                                    ol = row[l_idx]; nl = ol
                                    if "ม.1" in ol: nl=ol.replace("ม.1","ม.2")
                                    elif "ม.2" in ol: nl=ol.replace("ม.2","ม.3")
                                    elif "ม.3" in ol: nl="จบการศึกษา 🎓"
                                    elif "ม.4" in ol: nl=ol.replace("ม.4","ม.5")
                                    elif "ม.5" in ol: nl=ol.replace("ม.5","ม.6")
                                    elif "ม.6" in ol: nl="จบการศึกษา 🎓"
                                    if ol!=nl: row[l_idx]=nl; chg+=1
                                    new_r.append(row)
                            if chg > 0:
                                sheet.clear()
                                sheet.update('A1', [h] + new_r)
                                st.success(f"สำเร็จ {chg} คน")
                            else: st.info("ไม่มีข้อมูลต้องเปลี่ยน")
                        except Exception as e: st.error(f"Error: {e}")
                    else: st.error("รหัสผิด")
