import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 1. ตั้งค่าหน้ากระดาน (ต้องอยู่บนสุด ห้ามย้ายไปไว้ใน if check_login) ---
st.set_page_config(
    page_title="GATE VALVE CONTROL", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- 2. การเชื่อมต่อ Firebase (ปรับให้รองรับการโหลดซ้ำ) ---
if not firebase_admin._apps:
    try:
        # แนะนำให้ใช้ st.secrets สำหรับไฟล์ json เพื่อความปลอดภัยและรองรับการรันบน Cloud/Mobile
        cred = credentials.Certificate('dbsensor-eb39d-firebase-adminsdk-fbsvc-680b9bb5a7.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"Firebase Config Error: {e}")

ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 3. ฟังก์ชันบันทึกประวัติ ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except: pass

# --- 4. ฟังก์ชันดึงข้อมูลแบบ Safety ---
def get_safe_data():
    if 'cached_data' not in st.session_state:
        st.session_state.cached_data = {
            'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True,
            'motor_load': 0.0, 'schedule': [], 'online': False
        }
    try:
        data = ref.get()
        if data:
            st.session_state.cached_data.update(data)
            st.session_state.cached_data['online'] = True
        return st.session_state.cached_data
    except:
        st.session_state.cached_data['online'] = False
        return st.session_state.cached_data

# --- 5. ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            .login-container {
                background-color: rgba(30, 39, 46, 0.9);
                padding: 30px; border-radius: 15px;
                border: 1px solid #00ff88; text-align: center;
                margin-top: 50px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col2, _ = st.columns([0.2, 1, 0.2]) # ปรับสัดส่วนให้พอดีมือถือ
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.title("🔐 GATE CONTROL")
            u = st.text_input("Username", key="login_u")
            p = st.text_input("Password", type="password", key="login_p")
            if st.button("Login", use_container_width=True):
                user_data = user_ref.child(u).get()
                if user_data and user_data.get('password') == p:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    write_log("User Logged In")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# --- เริ่มการทำงานหลัก ---
if check_login():
    firebase_data = get_safe_data()

    # Sidebar
    st.sidebar.markdown(f"### 👤 User: {st.session_state.username}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    # CSS Styling (เพิ่ม Font-size ให้เหมาะกับมือถือ)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: #0d0f12; color: #e0e0e0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; font-size: 1.8rem !important; }
        .stButton>button { height: 60px !important; font-family: 'Orbitron'; }
        /* แก้ไข Sidebar ให้แคบลงสำหรับมือถือ */
        [data-testid="stSidebar"] { width: 200px !important; }
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<h2 style="font-family:\'Orbitron\'; color:#00ff88;">SYSTEM CONTROL</h2>', unsafe_allow_html=True)

    # Metrics (แสดงผล 2 คอลัมน์บนมือถือจะดูง่ายกว่า)
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.metric("Pressure", f"{firebase_data.get('live_pressure', 0.0):.2f} BAR")
        st.metric("Motor Load", f"{firebase_data.get('motor_load', 0.0)} A")
    with m_col2:
        st.metric("Rotation", f"{firebase_data.get('valve_rotation', 0.0):.1f} REV")
        st.metric("Time", datetime.now().strftime("%H:%M"))

    # Control Panel
    st.divider()
    is_auto = st.toggle("Auto Mode", value=firebase_data.get('auto_mode', True))
    
    # อัปเดต Auto Mode ทันทีที่เปลี่ยน
    if is_auto != firebase_data.get('auto_mode'):
        ref.update({'auto_mode': is_auto})
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔼 OPEN", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_command_time': str(datetime.now())})
            write_log("Manual Command: OPEN")
    with c2:
        if st.button("🔽 CLOSE", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_command_time': str(datetime.now())})
            write_log("Manual Command: CLOSE")

    if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
        ref.update({'command': 'STOP', 'emergency': True})
        write_log("EMERGENCY STOP")

    # --- ส่วนประวัติ ---
    with st.expander("📜 View Activity Logs"):
        try:
            logs = log_ref.order_by_key().limit_to_last(5).get()
            if logs:
                log_df = pd.DataFrame([logs[k] for k in reversed(logs.keys())])
                st.dataframe(log_df, use_container_width=True)
        except: pass

    # --- Auto Refresh แบบฉลาด (ไม่ทำบ่อยเกินไปสำหรับมือถือ) ---
    time.sleep(5) # ปรับเป็น 5 วินาทีเพื่อให้ iOS ไม่ตัดการทำงาน
    st.rerun()
