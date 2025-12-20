import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
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
SECRET_RESTORE_CODE = "POLICE2025" 
GAS_APP_URL = "https://script.google.com/macros/s/AKfycbxRf6z032SxMkiI4IxtUBvWLKeo1LmIQAUMByoXidy4crNEwHoO6h0B-3hT0X7Q5g/exec" 

# --- 2. Setup หน้าเว็บ ---
st.set_page_config(page_title="patwit moto.", page_icon="logo", layout="wide")

st.markdown("""
    <style>
        header { visibility: hidden !important; height: 0px !important; }
        footer { visibility: hidden !important; height: 0px !important; }
        [data-testid="stSidebar"] { display: none; }
        .block-container { padding-top: 2rem; }
        .score-box {
            font-size: 40px;
            font-weight: bold;
            padding: 10px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 10px;
        }
        .score-good { color: #198754; border: 2px solid #198754; background-color: #d1e7dd; }
        .score-bad { color: #dc3545; border: 2px solid #dc3545; background-color: #f8d7da; animation: blink 1s infinite; }
        @keyframes blink { 50% { opacity: 0.5; } }
    </style>
""", unsafe_allow_html=True)

# --- 3. ฟังก์ชันระบบ (Functions) ---
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

def update_point(std_id, action):
    try:
        sheet = connect_gsheet()
        # ค้นหาแถวจากรหัสนักเรียน (คอลัมน์ 3)
        cell = sheet.find(str(std_id), in_column=3)
        
        if cell:
            row_num = cell.row
            # 1. ดึงคะแนน (Col 12 / L) และเช็คค่าว่าง
            current_val = sheet.cell(row_num, 12).value
            score = int(current_val) if (current_val and str(current_val).isdigit()) else 100
            
            # 2. ดึงประวัติเก่า (Col 13 / M)
            old_history = sheet.cell(row_num, 13).value
            if not old_history or old_history == "-": old_history = ""
            
            new_score = score
            log_msg = ""
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # เงื่อนไขคะแนน
            if action == "no_helmet":
                new_score -= 5
                log_msg = f"[{timestamp}] หัก 5 คะแนน : ไม่สวมหมวกกันน็อค"
            elif action == "wrong_parking":
                new_score -= 5
                log_msg = f"[{timestamp}] หัก 5 คะแนน : จอดรถผิดที่"
            elif action == "driving_fast":
                new_score -= 5
                log_msg = f"[{timestamp}] หัก 5 คะแนน : ขับรถเร็ว/หวาดเสียว"
            elif action == "restore":
                new_score = 100
                log_msg = f"[{timestamp}] RESET : ฟื้นฟูคะแนนเต็ม 100"
            
            # รวมประวัติใหม่
            updated_history = old_history + "\n" + log_msg if old_history else log_msg
            
            # อัปเดตลง Sheet (12=Score, 13=History)
            sheet.update_cell(row_num, 12, new_score)
            sheet.update_cell(row_num, 13, updated_history)
            
            return True, new_score, "บันทึกข้อมูลสำเร็จ"
        return False, 0, "ไม่พบรหัสนักเรียน"
    except Exception as e:
        return False, 0, f"Error: {str(e)}"

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

# --- ฟังก์ชันสร้าง PDF เวอร์ชันปรับปรุง: ขยับภาพลงและป้องกันการทับซ้อน ---
def create_pdf(vals, img_url1, img_url2):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    try:
        pdfmetrics.registerFont(TTFont('THSarabunNew', 'THSarabunNew.ttf'))
        font_name = 'THSarabunNew'
    except:
        font_name = 'Helvetica'
    
    # 1. หัวกระดาษ
    try:
        c.drawImage("logo", 50, height - 85, width=50, height=50, mask='auto')
    except: pass 

    c.setFont(font_name, 24)
    c.drawCentredString(width/2, height - 50, "แบบทะเบียนประวัติรถจักรยานยนต์นักเรียน")
    c.setFont(font_name, 20)
    c.drawCentredString(width/2, height - 75, "โรงเรียนโพนทองพัฒนาวิทยา")
    c.line(50, height - 90, width - 50, height - 90)

    # 2. ข้อมูลนักเรียน (พิกัดคงที่ด้านบน)
    c.setFont(font_name, 16)
    name = str(vals[1]); std_id = str(vals[2]); 
    classroom = str(vals[3]); brand = str(vals[4]); 
    color = str(vals[5]); plate = str(vals[6]); 
    lic_status = str(vals[7]); tax_status = str(vals[8])
    
    try: 
        raw_score = str(vals[11]).strip()
        score = raw_score if raw_score.isdigit() else "100"
    except: score = "100"
    try: history_log = str(vals[12]) if vals[12] else "-"
    except: history_log = "-"

    c.drawString(60, height - 130, f"ชื่อ-นามสกุล: {name}")
    c.drawString(320, height - 130, f"ยี่ห้อ: {brand}")
    c.drawString(60, height - 155, f"รหัสนักเรียน: {std_id}")
    c.drawString(320, height - 155, f"สีรถ: {color}")
    c.drawString(60, height - 180, f"ระดับชั้น: {classroom}")
    c.setFont(font_name, 18)
    c.drawString(320, height - 180, f"ทะเบียน: {plate}")
    
    # กล่องคะแนน
    c.setStrokeColor(colors.black)
    c.rect(460, height - 120, 80, 50, fill=0) 
    c.setFont(font_name, 14)
    c.drawCentredString(500, height - 85, "คะแนนคงเหลือ")
    if int(score) < 60: c.setFillColor(colors.red)
    else: c.setFillColor(colors.green)
    c.setFont(font_name, 28)
    c.drawCentredString(500, height - 110, score)
    c.setFillColor(colors.black)

    # สถานะเอกสาร
    c.setFont(font_name, 16)
    lic_mark = "(/)" if "มี" in lic_status else "( )"
    tax_mark = "(/)" if "ครบ" in tax_status or "ปกติ" in tax_status else "( )"
    c.drawString(60, height - 210, f"สถานะเอกสาร:       {lic_mark} ใบขับขี่         {tax_mark} พรบ./ภาษี")

    # 3. ส่วนหลักฐานภาพถ่าย (ขยับลงมาอีกเพื่อไม่ให้ทับสถานะเอกสาร)
    c.setFont(font_name, 16)
    c.drawString(60, height - 255, "หลักฐานภาพถ่าย:")
    
    # --- ขยับ img_y ลงมาที่ 450 (จากเดิม 420) ---
    img_y = height - 450 
    
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

    # 4. ประวัติการหักคะแนน (ขยับลงตามรูปภาพ)
    # --- เริ่มใต้ขอบรูปภาพลงมาอีก 30 หน่วย ---
    history_y_start = img_y - 35 
    c.setFont(font_name, 16)
    c.drawString(60, history_y_start, "ประวัติการหักคะแนน / การฟื้นฟู:")
    c.line(60, history_y_start - 3, 530, history_y_start - 3)
    
    curr_y = history_y_start - 25
    c.setFont(font_name, 13)
    logs = history_log.split('\n')
    logs = [l for l in logs if l.strip() != ""] 
    recent_logs = logs[-6:] # แสดง 6 รายการล่าสุดเพื่อความสวยงาม

    if not recent_logs or (len(recent_logs) == 1 and recent_logs[0] == "-"):
        c.drawString(80, curr_y, "- ไม่มีการบันทึกประวัติ -")
    else:
        for log in recent_logs:
            if curr_y < 130: break # ป้องกันทับลายเซ็น
            c.drawString(80, curr_y, log)
            curr_y -= 18

    # 5. ส่วนลงชื่อ
    y_sign = 85
    c.setFont(font_name, 16)
    c.drawString(60, y_sign, "ลงชื่อ ....................................................... เจ้าของรถ")
    c.drawString(100, y_sign - 20, f"({name})")
    c.drawString(300, y_sign, "ลงชื่อ ....................................................... ครูผู้ตรวจสอบ")
    c.drawString(330, y_sign - 20, "(.......................................................)")
    
    c.setFont(font_name, 10)
    c.drawRightString(width - 30, 20, f"พิมพ์เมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    c.save()
    buffer.seek(0)
    return buffer

# ==========================================
# 4. ส่วนแสดงผล (UI)
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
# A. หน้านักเรียนลงทะเบียน
# ---------------------------------------
if st.session_state['page'] == 'student':
    st.info("📝 กรุณากรอกข้อมูลและแนบรูปรถ")
    
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            sub_c1, sub_c2 = st.columns([1.2, 2]) 
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
        
        submitted = st.form_submit_button("ส่งข้อมูล", use_container_width=True)

        if submitted:
            if fname and std_id and plate and photo1:
                try:
                    sheet = connect_gsheet()
                    existing_ids = sheet.col_values(3) 
                    
                    if std_id in existing_ids:
                        st.error(f"⚠️ รหัสนักเรียน '{std_id}' นี้สมัครไปแล้ว!") 
                    else:
                        with st.spinner("กำลังอัปโหลด..."):
                            clean_plate = plate.replace(" ", "")
                            link1 = upload_to_drive(photo1, f"{std_id}_{clean_plate}_FRONT.jpg")
                            link2 = ""
                            if photo2:
                                 link2 = upload_to_drive(photo2, f"{std_id}_{clean_plate}_SIDE.jpg")

                            if link1: 
                                # เพิ่ม 100 คะแนน และ History ว่างๆ
                                sheet.append_row([str(datetime.now()), name, std_id, f"{level}/{room}", brand, color, plate, license_status, tax_status, link1, link2, 100, ""])
                                st.success(f"✅ บันทึกข้อมูล {name} เรียบร้อย!")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("กรุณากรอกข้อมูลให้ครบ")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    c_staff_btn = st.columns([1, 2, 1])
    with c_staff_btn[1]:
        if st.button("🔐 สำหรับเจ้าหน้าที่/ตำรวจนักเรียน", use_container_width=True):
            go_to_teacher()
            st.rerun()

# ---------------------------------------
# B. หน้าเจ้าหน้าที่ตรวจสอบ
# ---------------------------------------
elif st.session_state['page'] == 'teacher':
    if st.button("🏠 กลับหน้าลงทะเบียน", on_click=go_to_student):
        st.rerun()
        
    st.markdown("### 👮 ส่วนสำหรับเจ้าหน้าที่")
    
    # Auto Logout
    if st.session_state.get('logged_in'):
        now = datetime.now().timestamp()
        last_active = st.session_state.get('last_active', now)
        if now - last_active > 3600:
            st.session_state['logged_in'] = False
            del st.session_state['last_active']
            st.error("⏳ หมดเวลาการใช้งาน กรุณาเข้าสู่ระบบใหม่")
        else:
            st.session_state['last_active'] = now

    if 'logged_in' not in st.session_state: 
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        pwd = st.text_input("กรอกรหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state['logged_in'] = True
                st.session_state['last_active'] = datetime.now().timestamp()
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if st.button("🚪 ออกจากระบบ"):
            st.session_state['logged_in'] = False
            if 'last_active' in st.session_state: del st.session_state['last_active']
            st.rerun()
        
        st.success("เข้าสู่ระบบเรียบร้อย")
        
        if st.button("🔄 โหลดข้อมูลล่าสุด", use_container_width=True):
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
            
            st.markdown("---")
            st.markdown("##### 🔍 ค้นหา / ตัดคะแนน / พิมพ์ประวัติ")
            
            c_input, c_btn = st.columns([3, 1])
            with c_input:
                search_query = st.text_input("ช่องค้นหา", label_visibility="collapsed", placeholder="พิมพ์ชื่อ, รหัสนักเรียน หรือ ทะเบียน...")
            with c_btn:
                btn_search = st.button("🔎 ค้นหา", use_container_width=True)

            if search_query:
                filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
                
                if len(filtered_df) == 0:
                    st.warning(f"❌ ไม่พบข้อมูล: '{search_query}'")
                else:
                    st.success(f"✅ พบ {len(filtered_df)} รายการ")
                    
                    for i, row in filtered_df.iterrows():
                        vals = row.tolist()
                        std_name = str(vals[1])
                        std_id = str(vals[2])
                        plate_num = str(vals[6])
                        
                        img1 = get_img_link(str(vals[9])) if len(vals) > 9 else None
                        img2 = get_img_link(str(vals[10])) if len(vals) > 10 else None
                        
                        try:
                            current_score = int(vals[11]) if len(vals) > 11 and str(vals[11]).isdigit() else 100
                        except:
                            current_score = 100
                            
                        # ดึงประวัติมาแสดงในเว็บด้วย (ถ้าอยากดู)
                        try: history_txt = str(vals[12])
                        except: history_txt = "-"

                        with st.expander(f"👤 {std_name} | 🆔 {std_id} | 🛵 {plate_num}", expanded=True):
                            
                            c_info, c_score = st.columns([2, 1])
                            with c_info:
                                st.write(f"**ชั้น:** {vals[3]} **ยี่ห้อ:** {vals[4]} **สี:** {vals[5]}")
                                ci1, ci2 = st.columns(2)
                                if img1: ci1.image(img1, caption="ด้านหน้า")
                                if img2: ci2.image(img2, caption="ด้านข้าง")
                                
                                # ปุ่ม PDF
                                if st.button(f"📄 โหลด PDF ประวัติ", key=f"gen_{i}"):
                                    with st.spinner("สร้าง PDF..."):
                                        try:
                                            pdf_bytes = create_pdf(vals, img1, img2)
                                            st.download_button(
                                                label="⬇️ ดาวน์โหลดเอกสาร",
                                                data=pdf_bytes,
                                                file_name=f"Moto_{plate_num}.pdf",
                                                mime="application/pdf",
                                                key=f"dl_{i}"
                                            )
                                        except Exception as e:
                                            st.error(f"Error PDF: {e}")

                            with c_score:
                                st.markdown("##### ❤️ คะแนนความประพฤติ")
                                score_class = "score-bad" if current_score < 60 else "score-good"
                                st.markdown(f'<div class="score-box {score_class}">{current_score}</div>', unsafe_allow_html=True)
                                if current_score < 60:
                                    st.caption("⚠️ คะแนนต่ำกว่าเกณฑ์!")
                                
                                # แสดงประวัติย่อๆ ในเว็บ
                                if history_txt and history_txt != "-":
                                    with st.expander("📜 ดูประวัติย้อนหลัง"):
                                        st.text(history_txt)
                                
                                st.markdown("---")
                                st.write("🚨 **แจ้งการกระทำผิด (-5):**")
                                
                                # เปลี่ยนเป็นระบบเลือก (Radio/Select) แทนปุ่มกดแยกกัน
                                action_selection = st.radio("เลือกความผิด:", 
                                                         ["ไม่สวมหมวก", "จอดผิดที่", "ขับรถเร็ว"], 
                                                         key=f"radio_{std_id}", horizontal=True)
                                
                                action_map = {
                                    "ไม่สวมหมวก": "no_helmet",
                                    "จอดผิดที่": "wrong_parking",
                                    "ขับรถเร็ว": "driving_fast"
                                }

                                # ปุ่มบันทึกข้อมูล
                                if st.button(f"บันทึกการหักคะแนน", key=f"btn_{std_id}"):
                                    st.session_state[f"confirm_{std_id}"] = True

                                # ระบบยืนยัน (Confirmation)
                                if st.session_state.get(f"confirm_{std_id}"):
                                    st.warning(f"⚠️ ยืนยันการหักคะแนนคุณ {std_name} ในข้อหา '{action_selection}' ใช่หรือไม่?")
                                    col_yes, col_no = st.columns(2)
                                    with col_yes:
                                        if st.button("✅ ใช่, ยืนยัน", key=f"yes_{std_id}"):
                                            res, ns, msg = update_point(std_id, action_map[action_selection])
                                            if res:
                                                st.success(f"{msg} คะแนนคงเหลือ: {ns}")
                                                st.session_state[f"confirm_{std_id}"] = False
                                                time.sleep(1.5)
                                                st.rerun()
                                    with col_no:
                                        if st.button("❌ ยกเลิก", key=f"no_{std_id}"):
                                            st.session_state[f"confirm_{std_id}"] = False
                                            st.rerun()
                                        else:
                                            st.error("❌ รหัสผิด")

            # --- ส่วนเลื่อนชั้นปี ---
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
