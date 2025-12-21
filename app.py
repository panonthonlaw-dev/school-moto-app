import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json
import requests
import base64
import time
import io
import re
import os
import textwrap
import plotly.express as px

# --- ส่วนของ PDF Library ---
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- 1. ตั้งค่า (Config) ---
SHEET_NAME = "Motorcycle_DB"
DRIVE_FOLDER_ID = "1WQGATGaGBoIjf44Yj_-DjuX8LZ8kbmBA" 
ADMIN_PASSWORD = "Patwit1150" 
UPGRADE_PASSWORD = "Patwitnext" 
GAS_APP_URL = "https://script.google.com/macros/s/AKfycbxRf6z032SxMkiI4IxtUBvWLKeo1LmIQAUMByoXidy4crNEwHoO6h0B-3hT0X7Q5g/exec" 

# --- 2. Setup หน้าเว็บ ---
st.set_page_config(page_title="patwit moto.", page_icon="logo", layout="wide")

st.markdown("""
    <style>
        header { visibility: hidden !important; height: 0px !important; }
        footer { visibility: hidden !important; height: 0px !important; }
        [data-testid="stSidebar"] { display: none; }
        .block-container { padding-top: 2rem; }
        .metric-card {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            text-align: center;
        }
        .metric-value { font-size: 2.2rem; font-weight: bold; color: #1e293b; line-height: 1; }
        .metric-percent { font-size: 1.1rem; color: #16a34a; font-weight: bold; margin-top: 5px; }
        .metric-label { font-size: 1rem; color: #64748b; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. ฟังก์ชันระบบ ---
if 'page' not in st.session_state:
    st.session_state['page'] = 'student'
if 'search_results_df' not in st.session_state:
    st.session_state['search_results_df'] = None
if 'edit_data' not in st.session_state:
    st.session_state['edit_data'] = None

def reset_results():
    st.session_state['search_results_df'] = None

def go_to_page(page_name):
    st.session_state['page'] = page_name
    st.rerun()

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

def upload_to_drive(file_obj, filename):
    try:
        file_content = file_obj.getvalue()
        base64_str = base64.b64encode(file_content).decode('utf-8')
        payload = {"folder_id": DRIVE_FOLDER_ID, "filename": filename, "file": base64_str, "mimeType": file_obj.type}
        response = requests.post(GAS_APP_URL, json=payload)
        result = response.json()
        if result.get("status") == "success": return result.get("link")
        else: raise Exception(f"Upload failed: {result.get('message')}")
    except Exception as e: raise Exception(f"เชื่อมต่อไม่ได้: {e}")

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

def create_pdf(vals, img_url1, img_url2):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    try:
        pdfmetrics.registerFont(TTFont('ThaiFont', 'THSarabunNew.ttf'))
        pdfmetrics.registerFont(TTFont('ThaiFontBold', 'THSarabunNewBold.ttf'))
        font_name = 'ThaiFont'
        font_bold = 'ThaiFontBold'
    except:
        font_name = 'Helvetica'
        font_bold = 'Helvetica-Bold'
    
    logo_file = next((f for f in ["logo.png", "logo.jpg", "logo"] if os.path.exists(f)), None)
    if logo_file:
        try: c.drawImage(logo_file, 50, height - 85, width=50, height=50, mask='auto')
        except: pass
    
    c.setFont(font_bold, 22)
    c.drawCentredString(width/2, height - 50, "แบบทะเบียนประวัติรถจักรยานยนต์นักเรียน")
    c.setFont(font_name, 18)
    c.drawCentredString(width/2, height - 72, "โรงเรียนโพนทองพัฒนาวิทยา")
    c.line(50, height - 85, width - 50, height - 85)
    
    c.setFont(font_name, 16)
    name, std_id, classroom, brand, color, plate = str(vals[1]), str(vals[2]), str(vals[3]), str(vals[4]), str(vals[5]), str(vals[6])
    lic_s, tax_s, hel_s = str(vals[7]), str(vals[8]), str(vals[9])
    note_text = str(vals[12]).strip() if len(vals) > 12 and str(vals[12]) != "nan" else ""

    c.drawString(60, height - 120, f"ชื่อ-นามสกุล: {name}")
    c.drawString(330, height - 120, f"ยี่ห้อรถ: {brand}")
    c.drawString(60, height - 145, f"รหัสนักเรียน: {std_id}")
    c.drawString(330, height - 145, f"สีรถ: {color}")
    c.drawString(60, height - 170, f"ระดับชั้น: {classroom}")
    c.setFont(font_bold, 16)
    c.drawString(330, height - 170, f"เลขทะเบียน: {plate}")
    
    c.setFont(font_name, 16)
    lic_m = "(/)" if "มี" in lic_s else "( )"
    tax_m = "(/)" if "ปกติ" in tax_s or "✅" in tax_s else "( )"
    hel_m = "(/)" if "มี" in hel_s else "( )"
    c.drawString(60, height - 200, f"สถานะเอกสาร:  {lic_m} ใบขับขี่    {tax_m} ภาษี/พรบ.    {hel_m} หมวกกันน็อค")
    
    c.drawString(60, height - 235, "หลักฐานภาพถ่ายรถ:")
    def draw_img(url, x, y):
        try:
            if url:
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    img = ImageReader(io.BytesIO(res.content))
                    c.drawImage(img, x, y, width=180, height=180, preserveAspectRatio=True)
        except: pass
    draw_img(img_url1, 70, height - 420)
    draw_img(img_url2, 300, height - 420)

    note_y = height - 460
    c.setFont(font_bold, 16)
    c.drawString(60, note_y, "บันทึกข้อความเพิ่มเติมโดยเจ้าหน้าที่:")
    c.setDash(1, 2)
    for i in range(5): c.line(60, note_y - 25 - (i*25), 530, note_y - 25 - (i*25))
    c.setDash()
    if note_text:
        c.setFont(font_name, 15)
        text_obj = c.beginText(70, note_y - 21)
        text_obj.setLeading(25)
        wrapped = textwrap.wrap(note_text, width=70)
        for line in wrapped[:5]: text_obj.textLine(line)
        c.drawText(text_obj)

    sign_y = 100
    c.setFont(font_name, 16)
    c.drawString(60, sign_y, "ลงชื่อ ....................................................... เจ้าของรถ")
    c.drawString(100, sign_y - 20, f"({name})")
    c.drawString(320, sign_y, "ลงชื่อ ....................................................... ครูผู้ตรวจสอบ")
    c.drawString(350, sign_y - 20, "(.......................................................)")
    thai_now = datetime.now() + timedelta(hours=7)
    c.setFont(font_name, 10)
    c.drawRightString(width - 30, 20, f"พิมพ์เมื่อ: {thai_now.strftime('%d/%m/%Y %H:%M')}")
    c.save()
    buffer.seek(0)
    return buffer

# --- 4. Main App UI ---
c_logo, c_title = st.columns([1, 8])
with c_logo:
    logo_file = next((f for f in ["logo.png", "logo.jpg", "logo"] if os.path.exists(f)), None)
    if logo_file: st.image(logo_file, width=90)
    else: st.write("🏍️")
with c_title: st.title("ระบบลงทะเบียนรถจักรยานยนต์โรงเรียนโพนทองพัฒนาวิทยา")
st.markdown("---")

if st.session_state['page'] == 'student':
    st.info("📝 สำหรับนักเรียน: ลงทะเบียนข้อมูลรถ")
    with st.form("reg_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            prefix = st.selectbox("คำนำหน้า", ["นาย", "นางสาว", "เด็กชาย", "เด็กหญิง", "นาง"])
            fname = st.text_input("ชื่อ-นามสกุล")
        std_id = c2.text_input("รหัสนักเรียน/รหัสเจ้าหน้าที่")
        c3, c4 = st.columns(2)
        level = c3.selectbox("ชั้น", ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6", "ครู,บุคลากร", "พ่อค้าแม่ค้า"])
        room_input = c4.text_input("ห้อง (ใส่เฉพาะเลข 0-13)", help="หากอยู่ห้อง 5 ให้ใส่เลข 5")
        c5, c6 = st.columns(2)
        brand = c5.selectbox("ยี่ห้อ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"])
        color = c6.text_input("สีรถ")
        plate = st.text_input("ทะเบียนรถ")
        doc_c1, doc_c2, doc_c3 = st.columns(3)
        lic_s = doc_c1.radio("ใบขับขี่", ["✅ มี", "❌ ไม่มี"], horizontal=True)
        tax_s = doc_c2.radio("ภาษี/พรบ", ["✅ ปกติ", "❌ ขาด"], horizontal=True)
        hel_s = doc_c3.radio("หมวกกันน็อค", ["✅ มี", "❌ ไม่มี"], horizontal=True)
        photo1 = st.file_uploader("รูปหลังรถ", type=['jpg','png','jpeg'])
        photo2 = st.file_uploader("รูปข้างรถ", type=['jpg','png','jpeg'])
        
        if st.form_submit_button("ส่งข้อมูลลงทะเบียน", use_container_width=True):
            valid_room = False
            try:
                room_num = int(room_input)
                if 0 <= room_num <= 13: valid_room = True
            except: pass
            if not valid_room: st.error("❌ กรุณาใส่ห้องให้ถูกต้อง (เลข 0 ถึง 13 เท่านั้น)")
            elif fname and std_id and plate and photo1:
                try:
                    sheet = connect_gsheet()
                    if str(std_id) in sheet.col_values(3): st.error("❌ รหัสนี้เคยลงทะเบียนไปแล้ว!")
                    else:
                        with st.spinner("⏳ บันทึกข้อมูล..."):
                            l1 = upload_to_drive(photo1, f"{std_id}_F.jpg")
                            l2 = upload_to_drive(photo2, f"{std_id}_S.jpg") if photo2 else ""
                            thai_now = datetime.now() + timedelta(hours=7)
                            full_name = f"{prefix}{fname}"
                            sheet.append_row([thai_now.strftime('%d/%m/%Y %H:%M'), full_name, str(std_id), f"{level}/{room_input}", brand, color, plate, lic_s, tax_s, hel_s, l1, l2, ""])
                            st.balloons(); st.success("✅ ลงทะเบียนสำเร็จ!")
                except Exception as e: st.error(f"Error: {e}")
            else: st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
    if st.button("🔐 สำหรับเจ้าหน้าที่", use_container_width=True): go_to_page('teacher')

elif st.session_state['page'] == 'dashboard':
    if st.button("⬅️ กลับหน้าจัดการข้อมูล"): go_to_page('teacher')
    st.subheader("📊 แดชบอร์ดวิเคราะห์สถิติจราจร")
    if 'df' in st.session_state:
        df = st.session_state.df
        total = len(df)
        
        # คัดกรองข้อมูลสำหรับแผนภูมิ
        lic_ok = df[df.iloc[:, 7].astype(str).str.contains("✅ มี")].shape[0]
        tax_ok = df[df.iloc[:, 8].astype(str).str.contains("ปกติ|✅")].shape[0]
        hel_ok = df[df.iloc[:, 9].astype(str).str.contains("✅ มี")].shape[0]

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.pie(values=[lic_ok, total-lic_ok], names=['✅ มีใบขับขี่', '❌ ไม่มี'], title="🪪 สถานะใบขับขี่", color_discrete_sequence=['#2ecc71', '#e74c3c'], hole=0.3)
            st.plotly_chart(fig1, use_container_width=True)
            
            fig2 = px.pie(values=[tax_ok, total-tax_ok], names=['✅ ภาษีปกติ', '❌ ภาษีขาด'], title="📝 สถานะภาษี/พรบ.", color_discrete_sequence=['#3498db', '#f39c12'], hole=0.3)
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            fig3 = px.pie(values=[hel_ok, total-hel_ok], names=['✅ มีหมวก', '❌ ไม่มี'], title="⛑️ การสวมหมวกกันน็อค", color_discrete_sequence=['#9b59b6', '#bdc3c7'], hole=0.3)
            st.plotly_chart(fig3, use_container_width=True)
            
            df['L_Group'] = df.iloc[:, 3].apply(lambda x: str(x).split('/')[0])
            fig4 = px.bar(df.groupby('L_Group').size().reset_index(name='จำนวน'), x='L_Group', y='จำนวน', title="📚 จำนวนรถแยกตามระดับชั้น", color='จำนวน', color_continuous_scale='Blues')
            st.plotly_chart(fig4, use_container_width=True)
    else: st.warning("กรุณากดดึงข้อมูลล่าสุดที่หน้าเจ้าหน้าที่ก่อน")

elif st.session_state['page'] == 'edit':
    st.subheader("✏️ แก้ไขข้อมูลรายบุคคล")
    v = st.session_state.edit_data
    with st.form("edit_form"):
        n_name = st.text_input("ชื่อ-นามสกุล", value=v[1]); n_class = st.text_input("ชั้น/ห้อง", value=v[3])
        n_brand = st.selectbox("ยี่ห้อ", ["Honda", "Yamaha", "Suzuki", "GPX", "Kawasaki", "อื่นๆ"], index=0)
        n_color = st.text_input("สีรถ", value=v[5]); n_plate = st.text_input("ทะเบียน", value=v[6])
        n_lic = st.radio("ใบขับขี่", ["✅ มี", "❌ ไม่มี"], index=0 if "มี" in v[7] else 1, horizontal=True)
        n_tax = st.radio("ภาษี/พรบ", ["✅ ปกติ", "❌ ขาด"], index=0 if "ปกติ" in v[8] or "✅" in v[8] else 1, horizontal=True)
        n_hel = st.radio("หมวกกันน็อค", ["✅ มี", "❌ ไม่มี"], index=0 if "มี" in v[9] else 1, horizontal=True)
        n_photo1 = st.file_uploader("เปลี่ยนรูปหลังรถ", type=['jpg','png','jpeg'])
        n_photo2 = st.file_uploader("เปลี่ยนรูปข้างรถ", type=['jpg','png','jpeg'])
        if st.form_submit_button("💾 บันทึกการแก้ไข"):
            try:
                sheet = connect_gsheet(); cell = sheet.find(str(v[2]))
                l1, l2 = v[10], v[11]
                if n_photo1: l1 = upload_to_drive(n_photo1, f"{v[2]}_F_new.jpg")
                if n_photo2: l2 = upload_to_drive(n_photo2, f"{v[2]}_S_new.jpg")
                sheet.update(f'B{cell.row}:L{cell.row}', [[n_name, v[2], n_class, n_brand, n_color, n_plate, n_lic, n_tax, n_hel, l1, l2]])
                st.success("แก้ไขสำเร็จ!"); del st.session_state.df; go_to_page('teacher')
            except Exception as e: st.error(f"Error: {e}")
    if st.button("ยกเลิก"): go_to_page('teacher')

elif st.session_state['page'] == 'teacher':
    if st.button("🏠 กลับหน้าหลัก"): go_to_page('student')
    if not st.session_state.get('logged_in'):
        pwd = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD: st.session_state.logged_in = True; st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if st.button("🚪 ออกจากระบบ"): st.session_state.logged_in = False; st.rerun()
        
        c_tool1, c_tool2 = st.columns(2)
        with c_tool1:
            if st.button("🔄 ดึงข้อมูลล่าสุดจากระบบ", use_container_width=True):
                try:
                    all_vals = connect_gsheet().get_all_values()
                    if len(all_vals) > 1:
                        headers = [h if h else f"Col_{i}" for i, h in enumerate(all_vals[0])]
                        st.session_state.df = pd.DataFrame(all_vals[1:], columns=headers[:len(all_vals[1])])
                        st.session_state.search_results_df = None; st.success("โหลดข้อมูลล่าสุดแล้ว!")
                except Exception as e: st.error(f"Error: {e}")
        with c_tool2:
            if st.button("📊 หน้ารายงานสถิติ (Dashboard)", use_container_width=True): go_to_page('dashboard')

        if 'df' in st.session_state:
            df = st.session_state.df
            total = len(df)
            lic_ok = df[df.iloc[:, 7].astype(str).str.contains("✅ มี")].shape[0]
            tax_ok = df[df.iloc[:, 8].astype(str).str.contains("ปกติ|✅")].shape[0]
            hel_ok = df[df.iloc[:, 9].astype(str).str.contains("✅ มี")].shape[0]
            
            # --- 📊 ส่วนสรุปผลตามเงื่อนไข (ตัวเลขใหญ่ + เปอร์เซ็นต์เขียวเล็ก) ---
            st.markdown("### 📊 สรุปผลภาพรวมระบบ")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            
            with m_col1:
                st.markdown(f"""<div class="metric-card"><div class="metric-value">{total}</div><div class="metric-percent">100%</div><div class="metric-label">🏍️ รถทั้งหมด</div></div>""", unsafe_allow_html=True)
            with m_col2:
                p = (lic_ok/total*100) if total > 0 else 0
                st.markdown(f"""<div class="metric-card"><div class="metric-value">{lic_ok}</div><div class="metric-percent">{p:.1f}%</div><div class="metric-label">🪪 มีใบขับขี่</div></div>""", unsafe_allow_html=True)
            with m_col3:
                p = (tax_ok/total*100) if total > 0 else 0
                st.markdown(f"""<div class="metric-card"><div class="metric-value">{tax_ok}</div><div class="metric-percent">{p:.1f}%</div><div class="metric-label">📝 ภาษีปกติ</div></div>""", unsafe_allow_html=True)
            with m_col4:
                p = (hel_ok/total*100) if total > 0 else 0
                st.markdown(f"""<div class="metric-card"><div class="metric-value">{hel_ok}</div><div class="metric-percent">{p:.1f}%</div><div class="metric-label">⛑️ มีหมวกกันน็อค</div></div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("🔎 ส่วนการตรวจสอบข้อมูล")
            q_txt = st.text_input("พิมพ์ ชื่อ, รหัส หรือ ทะเบียนรถ", key="q_txt", on_change=reset_results)
            if st.button("🔍 เริ่มค้นหาบุคคล", use_container_width=True) and q_txt:
                st.session_state.search_results_df = df[df.iloc[:, [1, 2, 6]].apply(lambda r: r.astype(str).str.contains(q_txt, case=False).any(), axis=1)]
            
            st.write("")
            col_f1, col_f2, col_f3 = st.columns(3)
            f_risk = col_f1.selectbox("🚨 กลุ่มปัญหา:", ["ทั้งหมด", "❌ ไม่มีใบขับขี่", "❌ ภาษีขาด", "❌ ไม่สวมหมวก"], on_change=reset_results)
            try: levels = ["ทั้งหมด"] + sorted(list(set([str(x).split('/')[0] for x in df.iloc[:, 3].unique()])))
            except: levels = ["ทั้งหมด"]
            f_level = col_f2.selectbox("📚 ระดับชั้น:", levels, on_change=reset_results)
            try: brands = ["ทั้งหมด"] + sorted(list(set(df.iloc[:, 4].unique())))
            except: brands = ["ทั้งหมด"]
            f_brand = col_f3.selectbox("🏍️ ยี่ห้อรถ:", brands, on_change=reset_results)
            if st.button("⚡ เริ่มการกรองข้อมูล", use_container_width=True, type="primary"):
                fdf = df.copy()
                if f_risk == "❌ ไม่มีใบขับขี่": fdf = fdf[fdf.iloc[:, 7].astype(str).str.contains("ไม่มี", na=False)]
                elif f_risk == "❌ ภาษีขาด": fdf = fdf[fdf.iloc[:, 8].astype(str).str.contains("ขาด|ไม่มี", na=False)]
                elif f_risk == "❌ ไม่สวมหมวก": fdf = fdf[fdf.iloc[:, 9].astype(str).str.contains("ไม่มี", na=False)]
                if f_level != "ทั้งหมด": fdf = fdf[fdf.iloc[:, 3].astype(str).str.contains(f_level, na=False)]
                if f_brand != "ทั้งหมด": fdf = fdf[fdf.iloc[:, 4] == f_brand]
                st.session_state.search_results_df = fdf

            if st.session_state.search_results_df is not None:
                res_df = st.session_state.search_results_df
                if not res_df.empty:
                    for i, row in res_df.iterrows():
                        v = row.tolist()
                        with st.expander(f"📍 {v[6]} | {v[1]}", expanded=True):
                            c_img, c_info = st.columns([2, 1])
                            with c_img:
                                i1, i2 = get_img_link(v[10]), get_img_link(v[11])
                                s1, s2 = st.columns(2)
                                if i1: s1.image(i1, caption="รูปหลังรถ")
                                if i2: s2.image(i2, caption="รูปข้างรถ")
                            with c_info:
                                st.write(f"**รหัส:** {v[2]} | **ชั้น:** {v[3]}\n**สถานะ:** {v[7]} / {v[8]} / {v[9]}")
                                st.download_button("⬇️ โหลด PDF ภาษาไทย", create_pdf(v, i1, i2), f"Profile_{v[6]}.pdf", key=f"pdf_{i}", mime="application/pdf")
                                if st.button("✏️ แก้ไขข้อมูลเบื้องต้น", key=f"e_{i}"): st.session_state.edit_data = v; go_to_page('edit')
                                st.write("---")
                                current_n = str(v[12]).strip() if len(v) > 12 and str(v[12]).lower() != "nan" else ""
                                new_n = st.text_area("บันทึกเจ้าหน้าที่...", value=current_n, key=f"n_{i}")
                                apwd = st.text_input("รหัส Patwitnext", type="password", key=f"apwd_{i}")
                                if st.button("💾 บันทึก", key=f"s_{i}"):
                                    if apwd == UPGRADE_PASSWORD:
                                        try:
                                            sheet = connect_gsheet(); cell = sheet.find(str(v[2]))
                                            sheet.update_acell(f'M{cell.row}', new_n); st.success("บันทึกแล้ว! กดดึงข้อมูลล่าสุดเพื่อดูผลใน PDF")
                                        except: st.error("บันทึกไม่ได้")
                                    else: st.error("รหัสผิด")
