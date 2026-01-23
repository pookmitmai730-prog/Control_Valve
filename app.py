import streamlit as st
import pandas as pd
import numpy as np
import time
import pytz
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 1. สำหรับ iOS: ต้องอยู่บนสุดและต้องกำหนดขอบเขตหน้าจอ ---
st.set_page_config(
    page_title="GATE VALVE CONTROL", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- CSS พิเศษสำหรับ iOS และ Mobile ---
st.markdown("""
    <style>
    /* บังคับ viewport ให้พอดีมือถือ */
    @viewport { width: device-width; zoom: 1.0; }
    
    /* ปรับแต่งปุ่มให้กดง่ายขึ้นบนนิ้วมือ (iOS Touch) */
    .stButton>button {
        min-height: 55px !important;
        border-radius: 10px !important;
        touch-action: manipulation;
    }
    
    /* ป้องกันตัวหนังสือ Metric เล็กเกินไปบน iPhone */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
    
    /* ซ่อนขอบที่อาจทำให้ต้องเลื่อนซ้ายขวาบน Safari */
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การเชื่อมต่อ Firebase (เหมือนเดิม) ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"Firebase Config Error: {e}")
        st.stop()

# อ้างอิง Node
ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')
local_tz = pytz.timezone('Asia/Bangkok')

def get_now():
    return datetime.now(local_tz)

# --- 3. ฟังก์ชันบันทึก Log ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": get_now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except: pass

# --- 4. ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        _, col2, _ = st.columns([0.1, 1, 0.1])
        with col2:
            st.title("🔐 LOGIN")
            u = st.text_input("Username", key="u_ios")
            p = st.text_input("Password", type="password", key="p_ios")
            if st.button("เข้าสู่ระบบ", use_container_width=True):
                user_data = user_ref.child(u).get()
                if user_data and user_data.get('password') == p:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    write_log("Logged in via Mobile")
                    st.rerun()
                else:
                    st.error("Login Failed")
        return False
    return True

# --- เริ่มการทำงานหลัก ---
if check_login():
    # สร้าง Container เพื่อให้ iOS ไม่ต้องโหลดหน้าใหม่ทั้งหมด
    placeholder = st.empty()
    
    with placeholder.container():
        # ดึงข้อมูล
        data = ref.get() or {}
        now_th = get_now()

        st.markdown(f"### ⚙️ GATE CONTROL: {st.session_state.username}")
        
        # --- Metrics: แสดงผลแบบ 2x2 บนมือถือจะดีกว่า ---
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1: st.metric("Pressure", f"{data.get('live_pressure', 0.0):.2f} BAR")
        with row1_col2: st.metric("Rotation", f"{data.get('valve_rotation', 0.0):.1f} REV")
        
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1: st.metric("Load", f"{data.get('motor_load', 0.0)} A")
        with row2_col2: st.metric("Time", now_th.strftime("%H:%M:%S"))

        # --- ส่วนควบคุม ---
        st.divider()
        is_auto = data.get('auto_mode', True)
        
        auto_toggle = st.toggle("Auto Mode", value=is_auto, key="ios_auto")
        if auto_toggle != is_auto:
            ref.update({'auto_mode': auto_toggle})
            write_log(f"Mode -> {'Auto' if auto_toggle else 'Manual'}")
            st.rerun()

        # ปุ่มกด (จัดเรียงให้เหมาะกับนิ้วมือบน iOS)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔼 OPEN", use_container_width=True, disabled=is_auto):
                ref.update({'command': 'OPEN', 'last_cmd_time': now_th.strftime("%H:%M:%S")})
                write_log("Manual OPEN")
        with c2:
            if st.button("🔽 CLOSE", use_container_width=True, disabled=is_auto):
                ref.update({'command': 'CLOSE', 'last_cmd_time': now_th.strftime("%H:%M:%S")})
                write_log("Manual CLOSE")
        
        if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})
            write_log("!!! STOP !!!")

        # ปุ่ม Logout ท้ายหน้าสำหรับมือถือ
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # --- หัวใจสำคัญสำหรับ iOS ---
    # ปรับเวลาการ Refresh ให้ช้าลงเล็กน้อย (6-10 วินาที) เพื่อไม่ให้ Safari บล็อก
    time.sleep(8)
    st.rerun()
