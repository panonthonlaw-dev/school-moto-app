import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import requests
import base64
import time

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

# --- 3. ฟังก์ชันระบบ ---
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
        # ค้นหา ID ในคอลัมน์ 3 (C)
        cell = sheet.find(str(std_id), in_column=3)
        
        if cell:
            row_num = cell.row
            # คะแนนอยู่ที่คอลัมน์ 12 (L)
            current_val = sheet.cell(row_num, 12).value
            
            if not current_val: current_val = 100
            score = int(current_val)
            
            new_score = score
            msg = ""
            
            if action == "no_helmet":
                new_score -= 5
                msg = "❌ หัก 5 คะแนน (ไม่สวมหมวก)"
            elif action == "wrong_parking":
                new_score -= 5
                msg = "❌ หัก 5 คะแนน (จอดผิดที่)"
            elif action == "driving_fast":
                new_score -= 5
                msg = "❌ หัก 5 คะแนน (ขับรถเร็ว)"
            elif action == "restore":
                new_score = 100
                msg = "✨ ฟื้นฟูคะแนนเรียบร้อย!"
            
            sheet.update_cell(row_num, 12, new_score)
            return True, new_score, msg
        else:
            return False, 0, "ไม่พบข้อมูลนักเรียน"
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
                                # เพิ่ม 100 คะแนนเริ่มต้น (คอลัมน์ 12)
                                sheet.append_row([str(datetime.now()), name, std_id, f"{level}/{room}", brand, color, plate, license_status, tax_status, link1, link2, 100])
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
            st.markdown("##### 🔍 ค้นหาและจัดการคะแนน")
            
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
                        
                        try:
                            # Index 11 = คอลัมน์ L (Score)
                            current_score = int(vals[11]) if len(vals) > 11 and str(vals[11]).isdigit() else 100
                        except:
                            current_score = 100

                        with st.container():
                            st.info(f"👤 **{std_name}** | 🆔 {std_id} | 🛵 {plate_num}")
                            
                            c_score, c_action = st.columns([1, 2])
                            
                            with c_score:
                                st.write("คะแนนความประพฤติ")
                                score_class = "score-bad" if current_score < 60 else "score-good"
                                st.markdown(f'<div class="score-box {score_class}">{current_score}</div>', unsafe_allow_html=True)
                                if current_score < 60:
                                    st.caption("⚠️ คะแนนต่ำกว่าเกณฑ์!")

                            with c_action:
                                st.write("🚨 **แจ้งการกระทำผิด (-5 คะแนน):**")
                                b1, b2, b3 = st.columns(3)
                                
                                if b1.button("⛑️ ไม่สวมหมวก", key=f"h_{std_id}"):
                                    res, ns, msg = update_point(std_id, "no_helmet")
                                    if res:
                                        st.success(f"{msg} เหลือ {ns}")
                                        time.sleep(1) 
                                        st.rerun() 
                                
                                if b2.button("🅿️ จอดผิดที่", key=f"p_{std_id}"):
                                    res, ns, msg = update_point(std_id, "wrong_parking")
                                    if res:
                                        st.success(f"{msg} เหลือ {ns}")
                                        time.sleep(1)
                                        st.rerun()

                                if b3.button("🏍️ ขับรถเร็ว", key=f"f_{std_id}"):
                                    res, ns, msg = update_point(std_id, "driving_fast")
                                    if res:
                                        st.success(f"{msg} เหลือ {ns}")
                                        time.sleep(1)
                                        st.rerun()
                                
                                with st.expander("✨ ฟื้นฟูคะแนน (ใช้รหัสลับ)"):
                                    restore_code = st.text_input("ใส่รหัสลับ", type="password", key=f"code_{std_id}")
                                    if st.button("ยืนยันฟื้นฟู", key=f"res_{std_id}"):
                                        if restore_code == SECRET_RESTORE_CODE:
                                            res, ns, msg = update_point(std_id, "restore")
                                            if res:
                                                st.success(msg)
                                                time.sleep(1)
                                                st.rerun()
                                        else:
                                            st.error("❌ รหัสลับไม่ถูกต้อง")
                            st.markdown("---")

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
