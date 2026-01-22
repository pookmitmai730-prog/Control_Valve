import streamlit as st
import pandas as pd
import numpy as np
import time
import pytz  # เพิ่มการ import pytz
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 0. ฟังก์ชันจัดการเวลาท้องถิ่น (ไทย) ---
def get_local_time():
    # กำหนด timezone เป็นประเทศไทย
    local_tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(local_tz)

# --- 1. ตั้งค่าหน้ากระดาน (ต้องอยู่บนสุด) ---
st.set_page_config(page_title="GATE VALVE CONTROL", layout="wide", initial_sidebar_state="collapsed")

# --- 2. ตั้งค่า Firebase ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate('dbsensor-eb39d-firebase-adminsdk-fbsvc-680b9bb5a7.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"Firebase Config Error: {e}")

ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- ฟังก์ชันบันทึกประวัติ (ปรับเวลา) ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": get_local_time().strftime("%Y-%m-%d %H:%M:%S") # ใช้เวลาไทย
        })
    except: pass

# --- ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            .login-container {
                background-color: rgba(30, 39, 46, 0.9);
                padding: 40px; border-radius: 15px;
                border: 1px solid #00ff88; text-align: center;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col2, _ = st.columns([1, 1.2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.title("🔐 GATE CONTROL")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
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

# --- ดึงข้อมูลแบบ Safety ---
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

# --- เริ่มการทำงานหลัก ---
if check_login():
    firebase_data = get_safe_data()
    now_thai = get_local_time() # ดึงเวลาไทยมาเก็บไว้ใช้งาน

    # Sidebar
    st.sidebar.markdown(f"### 👤 User: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    if not firebase_data['online']:
        st.warning("⚠️ Offline Mode: แสดงค่าล่าสุดจากหน่วยความจำ")
    else:
        st.sidebar.success("● System Online")

    # --- CSS Styling ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle, #1a1f25 0%, #0d0f12 100%); color: #e0e0e0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; }
        .stButton>button { background: linear-gradient(135deg, #1e272e 0%, #2f3640 100%) !important; color: #00ff88 !important; border: 1px solid #00ff88 !important; font-family: 'Orbitron'; }
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-family:\'Orbitron\'; text-shadow: 0 0 10px #00ff88;">SYSTEM CONTROL</h1>', unsafe_allow_html=True)

    # --- Metrics (ใช้เวลาไทย) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Live Pressure", f"{firebase_data.get('live_pressure', 0.0):.2f} BAR")
    with c2: st.metric("Valve Rotation", f"{firebase_data.get('valve_rotation', 0.0):.1f} REV")
    with c3: st.metric("Motor Load", f"{firebase_data.get('motor_load', 0.0)} A")
    with c4: st.metric("System Time", now_thai.strftime("%H:%M:%S")) # แสดงเวลาไทย

    # --- Main Content ---
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown('### 🚨 PRESSURE TREND')
        if 'history_df' not in st.session_state:
            # ใช้เวลาไทยใน index ของกราฟ
            time_index = pd.date_range(start=now_thai-timedelta(days=3), end=now_thai, freq='1H')
            st.session_state.history_df = pd.DataFrame({'Pressure': np.random.uniform(3.5, 4.5, size=len(time_index))}, index=time_index)
        st.line_chart(st.session_state.history_df, color="#ff3e3e", height=250)

    # --- Control Panel ---
    st.divider()
    is_auto = st.toggle("Auto Mode", value=firebase_data.get('auto_mode', True))
    
    if is_auto != firebase_data.get('auto_mode'):
        ref.update({'auto_mode': is_auto})
        st.rerun()

    ctrl_1, ctrl_2, ctrl_4 = st.columns([1, 1, 1])
    with ctrl_1:
        if st.button("🔼 Open Valve", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_command_time': now_thai.strftime("%Y-%m-%d %H:%M:%S")})
            write_log("Manual Command: OPEN")
    with ctrl_2:
        if st.button("🔽 Close Valve", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_command_time': now_thai.strftime("%Y-%m-%d %H:%M:%S")})
            write_log("Manual Command: CLOSE")
    with ctrl_4:
        if st.button("🚨 Emergency Stop", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})
            write_log("EMERGENCY STOP")

    # --- Logs ---
    st.markdown("### 📜 RECENT ACTIVITY LOGS")
    try:
        logs = log_ref.order_by_key().limit_to_last(10).get()
        if logs:
            log_list = [logs[key] for key in reversed(logs.keys())]
            st.table(pd.DataFrame(log_list))
    except: pass

    time.sleep(5)
    st.rerun()
