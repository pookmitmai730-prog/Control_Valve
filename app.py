import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 1. ตั้งค่าหน้ากระดาน ---
st.set_page_config(
    page_title="ระบบควบคุมประตูน้ำ น.นาแก",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. การเชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        p_key = fb_dict["private_key"].strip()
        if "\\n" in p_key:
            p_key = p_key.replace("\\n", "\n")
        fb_dict["private_key"] = p_key
        
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"⚠️ ไม่สามารถเชื่อมต่อ Firebase ได้: {e}")
        st.stop()

ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 3. ฟังก์ชันการทำงานพื้นฐาน ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except:
        pass

def init_default_user():
    try:
        if user_ref.get() is None:
            user_ref.child('admin').set({
                'password': 'papak123',
                'role': 'super_admin'
            })
    except:
        pass

@st.cache_data(ttl=2)
def get_live_data():
    try:
        data = ref.get()
        if data:
            data['online'] = True
            return data
    except:
        pass
    return {
        'live_pressure': 0.0, 'valve_rotation': 0.0, 
        'auto_mode': True, 'motor_load': 0.0, 
        'schedule': [], 'online': False
    }

# --- 4. ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&display=swap');
            html, body, [class*="st-"], .stMarkdown, p, div {
                font-family: 'Noto Sans Thai', sans-serif !important;
            }
            .login-box {
                background-color: rgba(30, 39, 46, 0.95);
                padding: 50px;
                border-radius: 20px;
                border: 2px solid #00ff88;
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
                text-align: center;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            st
