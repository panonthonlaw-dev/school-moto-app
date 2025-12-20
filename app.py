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
ADMIN_PASSWORD = "Patwit1150" # รหัสเข้าหน้าเจ้าหน้าที่
SECRET_RESTORE_CODE = "POLICE2025" # รหัสฟื้นฟูคะแนน
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
        cell = sheet.find(str(std_id), in_column=3)
        if cell:
            row_num = cell.row
            current_val = sheet.cell(row_num, 12).value
            score = int(current_val) if (current_val and str(current_val).isdigit()) else 100
            old_history = sheet.cell(row_num, 13).value
            if not old_history or old_history == "-": old_history = ""
            new_score = score
            log_msg = ""
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
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
            updated_history = old_history + "\n" + log_msg if old_history else log_msg
            sheet.update_cell(row_num, 12, new_score)
            sheet.update_cell(row_num, 13, updated_history)
            return True, new_score, "สำเร็จ"
        return False, 0, "ไม่พบข้อมูล"
    except Exception as e: return False, 0, f"Error: {e}"

def upload_to_drive(file_obj, filename):
    if "script.google.com" not in GAS_APP_URL:
        st.error("🚨 กรุณาใส่ URL Web App")
        return None
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
        pdfmetrics.registerFont(TTFont('THSarabunNew', 'THSarabunNew.ttf'))
        font_name = 'THSarabunNew'
    except: font_name = 'Helvetica'
    try: c.drawImage("logo", 50, height - 85, width=50, height=50, mask='auto')
    except: pass 
    c.setFont(font_name, 24)
    c.drawCentredString(width/2, height - 50, "แบบทะเบียนประวัติรถจักรยานยนต์นักเรียน")
    c.setFont(font_name, 20)
    c.drawCentredString(width/2, height - 75, "โรงเรียนโพนทองพัฒนาวิทยา")
    c.line(50, height - 90, width - 50, height - 90)
    c.setFont(font_name, 16)
    name, std_id, classroom, brand, color, plate, lic_status, tax_status = str(vals[1]), str(vals[2]), str(vals[3]), str(vals[4]), str(vals[5]), str(vals[6]), str(vals[7]), str(vals[8])
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
    c.setStrokeColor(colors.black)
    c.rect(460, height - 120, 80, 50, fill=0) 
    c.setFont(font_name, 14)
    c.drawCentredString(500, height - 85, "คะแนนคงเหลือ")
    if int(score) < 60: c.setFillColor(colors.red)
    else: c.setFillColor(colors.green)
    c.setFont(font_name, 28)
    c.drawCentredString(500, height - 110, score)
    c.setFillColor(colors.black)
    c.setFont(font_name, 16)
    lic_mark = "(/)" if "มี" in lic_status else "( )"
    tax_mark = "(/)" if "ครบ" in tax_status or "ปกติ" in tax_status else "( )"
    c.drawString(60, height - 210, f"สถานะเอกสาร:       {lic_mark} ใบขับขี่         {tax_mark} พรบ./ภาษี")
    c.setFont(font_name, 16)
    c.drawString(60, height - 255, "หลักฐานภาพถ่าย:")
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
    history_y_start = img_y - 35 
    c.setFont(font_name, 16)
    c.drawString(60, history_y_start, "ประวัติการหักคะแนน / การฟื้นฟู:")
    c.line(60, history_y_start - 3, 530, history_y_start - 3)
    curr_y = history_y_start - 25
    c.setFont(font_name, 13)
    logs = [l for l in history_log.split('\n') if l.strip() != ""]
    recent_logs = logs[-6:]
    if not recent_logs or (len(recent_logs) == 1 and recent_logs[0] == "-"): c.drawString(80, curr_y, "- ไม่มีการบันทึกประวัติ -")
    else:
        for log in recent_logs:
            if curr_y < 130: break
            c.drawString(80, curr_y, log)
            curr_y -= 18
    y_sign = 85
