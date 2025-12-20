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
                msg = "❌ หัก 5 คะแนน
