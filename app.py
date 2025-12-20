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
ADMIN_PASSWORD = "Patwit1150"
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
    st.title("ระบบลงทะเบียนรถจักรยานยนต์โรงเรียนโพนทองพัฒนาวิทยา")
    
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
            prefix = sub_c1.selectbox("คำนำหน้า", ["นาย", "นางสาว", "เด็กชาย", "เด็กหญิง", "นาง", ])
            if prefix == "อื่นๆ":
                prefix = sub_c1.text_input("ระบุคำนำหน้า", key="other_prefix")
            fname = sub_c2.text_input("ชื่อ-นามสกุล (ไม่ต้องใส่คำนำหน้า)")
            name = f"{prefix}{fname}" if fname else ""

        std_id = c2.text_input("รหัสนักเรียน (ครู/พ่อค้าแม้ค้าใช้วัน เดือน พ.ศ.เกิด เช่น020923)")
        
        c3, c4 = st.columns(2)
        level = c3.selectbox("ชั้น", ["ม.1","ม.2","ม.3","ม.4","ม.5","ม.6","ครู/บุคลากร","พ่อค้าแม่ค้า"])
        room = c4.text_input("ห้อง")
        
        st.markdown("---")
        
        c5, c6 = st.columns(2)
        brand = c5.selectbox("ยี่ห้อ", ["Honda","Yamaha","Suzuki","GPX","kawasaki","อื่นๆ"])
        color = c6.text_input("สีรถ")
        
        plate = st.text_input("ทะเบียน พร้อมจังหวัด (ตัวอย่าง กก1234 ร้อยเอ็ด)")
        
        st.markdown("##### 📄 ข้อมูลเอกสาร")
        doc_col1, doc_col2 = st.columns(2)
        license_status = doc_col1.radio("ใบขับขี่", ["✅ มีใบขับขี่", "❌ ไม่มี"], horizontal=True)
        tax_status = doc_col2.radio("พรบ. และ ภาษี", ["✅ ต่อครบถ้วน", "❌ ขาด/ไม่แน่ใจ"], horizontal=True)
        
        st.markdown("### 📸 ถ่ายรูปรถ (2 มุม)")
        col_img1, col_img2 = st.columns(2)
        photo1 = col_img1.file_uploader("1. รูปด้านหลัง (เห็นทะเบียน)", type=['jpg','png','jpeg'], key="p1")
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
        if st.button("🔐 สำหรับเจ้าหน้าที่/ตำรวจนักเรียน", use_container_width=True):
            go_to_teacher()
            st.rerun()
            # ---------------------------------------
# ---------------------------------------
# 👮 หน้าเจ้าหน้าที่ตรวจสอบ (Part 3.1 + Auto Logout)
# ---------------------------------------
elif st.session_state['page'] == 'teacher':
    # ปุ่มกลับหน้าหลัก
    if st.button("🏠 กลับหน้าลงทะเบียน", on_click=go_to_student):
        st.rerun()
        
    st.markdown("### 👮 ส่วนสำหรับเจ้าหน้าที่")
    
    # --- 🕒 ส่วนเช็คเวลาหมดอายุ (Auto Logout) ---
    # ถ้ามีการล็อกอินค้างไว้ ให้เช็คเวลา
    if st.session_state.get('logged_in'):
        # ดึงเวลาปัจจุบัน (timestamp)
        now = datetime.now().timestamp()
        last_active = st.session_state.get('last_active', now)
        
        # ถ้าเวลาผ่านไปเกิน 3600 วินาที (1 ชั่วโมง)
        if now - last_active > 3600:
            st.session_state['logged_in'] = False
            del st.session_state['last_active'] # ลบตัวแปรเวลาทิ้ง
            st.error("⏳ หมดเวลาการใช้งาน (Session Expired) กรุณาเข้าสู่ระบบใหม่")
            # ไม่สั่ง rerun ทันที เพื่อให้เห็นข้อความแจ้งเตือนก่อน
        else:
            # ถ้ายังไม่หมดเวลา ให้รีเซ็ตเวลาเป็นปัจจุบัน (นับถอยหลังใหม่)
            st.session_state['last_active'] = now

    # --- จบส่วนเช็คเวลา ---

    if 'logged_in' not in st.session_state: 
        st.session_state['logged_in'] = False

    # ถ้ายังไม่ได้ล็อกอิน (หรือเพิ่งโดนเตะออกมา)
    if not st.session_state['logged_in']:
        pwd = st.text_input("กรอกรหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state['logged_in'] = True
                # ✅ บันทึกเวลาเริ่มต้นตอนล็อกอินสำเร็จ
                st.session_state['last_active'] = datetime.now().timestamp()
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        # ส่วนแสดงผลหลังล็อกอิน
        if st.button("🚪 ออกจากระบบ"):
            st.session_state['logged_in'] = False
            if 'last_active' in st.session_state: del st.session_state['last_active']
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
                lic = df[df.iloc[:, 7].astype(str).str.contains("มี", na=False)].shape[0]
                tax = df[df.iloc[:, 8].astype(str).str.contains("ครบ|ปกติ", na=False)].shape[0]
                
                if total > 0:
                    lic_pct = (lic / total) * 100
                    tax_pct = (tax / total) * 100
                else:
                    lic_pct = 0; tax_pct = 0
            except: 
                lic=0; tax=0; lic_pct=0; tax_pct=0

            # แสดงผล
            c1, c2, c3 = st.columns(3)
            c1.metric("🏍️ รถทั้งหมด", f"{total} คัน")
            c2.metric("🪪 มีใบขับขี่", f"{lic} คน", delta=f"{lic_pct:.1f}%")
            c3.metric("📝 พรบ./ภาษี", f"{tax} คัน", delta=f"{tax_pct:.1f}%")
            
            st.markdown("---")
       # (Part 3.2: วางต่อท้ายสุด - แก้ไข Syntax Error แล้ว)
            
            # --- Import ตัวทำ PDF ---
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.utils import ImageReader
            import io

            # ฟังก์ชันสร้าง PDF
            def create_pdf(vals, img_url1, img_url2):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4
                
                # 1. โหลดฟอนต์ภาษาไทย
                try:
                    pdfmetrics.registerFont(TTFont('THSarabunNew', 'THSarabunNew.ttf'))
                    font_name = 'THSarabunNew'
                except:
                    font_name = 'Helvetica'
                
                # 2. หัวกระดาษ & โลโก้
                # --- จุดที่เคย Error แก้ไขให้แล้วครับ (มี except รองรับชัดเจน) ---
                try:
                    c.drawImage("logo.png", 50, height - 85, width=50, height=50, mask='auto')
                except Exception:
                    pass # ถ้าหาไฟล์โลโก้ไม่เจอ ให้ข้ามไป ไม่ต้อง Error
                # -------------------------------------------------------

                c.setFont(font_name, 24)
                c.drawCentredString(width/2, height - 50, "แบบทะเบียนประวัติรถจักรยานยนต์นักเรียน")
                c.setFont(font_name, 20)
                c.drawCentredString(width/2, height - 75, "โรงเรียนโพนทองพัฒนาวิทยา")
                c.line(50, height - 90, width - 50, height - 90)

                # 3. ข้อมูลส่วนตัว
                y = height - 130
                c.setFont(font_name, 16)
                
                name = str(vals[1]); std_id = str(vals[2]); 
                classroom = str(vals[3]); brand = str(vals[4]); 
                color = str(vals[5]); plate = str(vals[6]); 
                lic_status = str(vals[7]); tax_status = str(vals[8])

                c.drawString(60, y, f"ชื่อ-นามสกุล: {name}")
                c.drawString(60, y-25, f"รหัสนักเรียน: {std_id}")
                c.drawString(60, y-50, f"ระดับชั้น: {classroom}")
                
                # 4. ข้อมูลรถ
                c.drawString(300, y, f"ยี่ห้อ: {brand}")
                c.drawString(300, y-25, f"สีรถ: {color}")
                c.setFont(font_name, 20)
                c.drawString(300, y-55, f"ทะเบียน: {plate}")
                c.rect(295, y-60, 150, 25) 
                
                # 5. สถานะ
                c.setFont(font_name, 16)
                y_status = y - 90
                lic_mark = "(/)" if "มี" in lic_status else "( )"
                tax_mark = "(/)" if "ครบ" in tax_status or "ปกติ" in tax_status else "( )"
                c.drawString(60, y_status, f"สถานะเอกสาร:      {lic_mark} ใบขับขี่         {tax_mark} พรบ./ภาษี")
                
                # 6. รูปภาพหลักฐาน
                y_img = y_status - 220
                def draw_img(url, x, y):
                    try:
                        if url:
                            res = requests.get(url, timeout=5)
                            if res.status_code == 200:
                                img = ImageReader(io.BytesIO(res.content))
                                c.drawImage(img, x, y, width=200, height=200, preserveAspectRatio=True)
                            else: c.drawString(x, y+100, "โหลดรูปไม่ได้")
                    except: c.drawString(x, y+100, "Error รูปภาพ")

                c.drawString(60, y_img + 210, "หลักฐานภาพถ่าย:")
                draw_img(img_url1, 60, y_img)
                draw_img(img_url2, 300, y_img)

                # 7. ลายเซ็น
                y_sign = 100
                c.drawString(60, y_sign, "ลงชื่อ ....................................................... เจ้าของรถ")
                c.drawString(100, y_sign-20, f"({name})")
                c.drawString(300, y_sign, "ลงชื่อ ....................................................... ครูผู้ตรวจสอบ")
                c.drawString(330, y_sign-20, "(.......................................................)")
                
                c.setFont(font_name, 12)
                c.drawRightString(width - 30, 30, f"พิมพ์เมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                
                c.save()
                buffer.seek(0)
                return buffer

            # --- ส่วนค้นหา + ปุ่มกด ---
            st.markdown("##### 🔍 ค้นหาข้อมูล")
            c_input, c_btn = st.columns([4, 1])
            
            with c_input:
                search_query = st.text_input("ช่องค้นหา", label_visibility="collapsed", placeholder="พิมพ์ชื่อ หรือ เลขทะเบียน...")
            
            with c_btn:
                btn_search = st.button("🔎 ค้นหา", use_container_width=True)

            # --- LOGIC แสดงผล ---
            if not search_query:
                st.info("👆 กรุณาพิมพ์ข้อมูล และกดปุ่ม **'ค้นหา'**")
            else:
                filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
                
                if len(filtered_df) == 0:
                    st.warning(f"❌ ไม่พบข้อมูล: '{search_query}'")
                else:
                    st.success(f"✅ พบข้อมูล {len(filtered_df)} รายการ")
                    
                    def get_img_link(url):
                        url = str(url).strip()
                        if not url: return None
                        import re
                        file_id = None
                        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
                        if match: file_id = match.group(1)
                        else: 
                            match = re.search(r'id=([a-zA-Z0-9_-
