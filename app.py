import streamlit as st

# --- ต้องอยู่บรรทัดแรกสุด ---
st.set_page_config(page_title="GATE VALVE CONTROL", layout="wide")

import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 1. ตั้งค่า Firebase (ฉบับแก้ RefreshError) ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        
        # ล้างช่องว่างที่อาจติดมาจากการก๊อปปี้
        p_key = fb_dict["private_key"].strip()
        
        # ตรวจสอบว่ามี \n ในรูปแบบตัวอักษรหรือไม่ ถ้ามีให้แปลงเป็นขึ้นบรรทัดใหม่จริง
        if "\\n" in p_key:
            p_key = p_key.replace("\\n", "\n")
        
        fb_dict["private_key"] = p_key
        
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"⚠️ Firebase Config Error: {e}")
        st.stop()

# อ้างอิง Node หลัก
ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 2. ฟังก์ชันย่อย ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except: pass

def init_default_user():
    try:
        if user_ref.get() is None:
            user_ref.child('admin').set({'password': 'papak123', 'role': 'super_admin'})
    except: pass

@st.cache_data(ttl=2) # ช่วยให้การดึงข้อมูลเร็วขึ้นและไม่กระตุก
def get_safe_data():
    try:
        data = ref.get()
        if data:
            data['online'] = True
            return data
    except:
        pass
    return {'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True, 'motor_load': 0.0, 'schedule': [], 'online': False}

# --- 3. ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            .login-container { background-color: rgba(30, 39, 46, 0.9); padding: 40px; border-radius: 15px; border: 1px solid #00ff88; text-align: center; }
            </style>
        """, unsafe_allow_html=True)
        
        _, col2, _ = st.columns([1, 1.2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.title("🔐 GATE CONTROL")
            u = st.text_input("Username", key="login_user")
            p = st.text_input("Password", type="password", key="login_pass")
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

# --- 4. Main App ---
if check_login():
    init_default_user()
    firebase_data = get_safe_data()

    # Sidebar
    st.sidebar.markdown(f"### 👤 User: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    if not firebase_data['online']:
        st.sidebar.warning("⚠️ Offline Mode")
    else:
        st.sidebar.success("● System Online")

    # CSS
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle, #1a1f25 0%, #0d0f12 100%); color: #e0e0e0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; }
        .section-head-red { border-bottom: 1px solid #333; color: #ff3e3e; font-family: 'Orbitron'; font-size: 1.1rem; padding-bottom: 5px; margin-bottom: 15px; }
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-family:\'Orbitron\'; text-shadow: 0 0 10px #00ff88;">SYSTEM CONTROL VALVE PAPAK</h1>', unsafe_allow_html=True)

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Live Pressure", f"{firebase_data.get('live_pressure', 0.0):.2f} BAR")
    with c2: st.metric("Valve Rotation", f"{firebase_data.get('valve_rotation', 0.0):.1f} REV")
    with c3: st.metric("Motor Load", f"{firebase_data.get('motor_load', 0.0)} A")
    with c4: st.metric("System Time", datetime.now().strftime("%H:%M:%S"))

    # Main Panels
    col_left, col_right = st.columns([1.5, 1])
    with col_left:
        st.markdown('<div class="section-head-red">🚨 PRESSURE TREND</div>', unsafe_allow_html=True)
        if 'history_df' not in st.session_state:
            time_index = pd.date_range(start=datetime.now()-timedelta(days=3), end=datetime.now(), freq='1H')
            st.session_state.history_df = pd.DataFrame({'Pressure': np.random.uniform(3.5, 4.5, size=len(time_index))}, index=time_index)
        st.line_chart(st.session_state.history_df, color="#ff3e3e", height=250)

    with col_right:
        st.markdown('### 📋 SCHEDULE SETTING')
        current_schedule = pd.DataFrame(firebase_data.get('schedule', [{"START_TIME": "00:00", "TARGET": 0.0}]))
        edited_df = st.data_editor(current_schedule, use_container_width=True, num_rows="dynamic")
        if st.button("Apply & Sync"):
            ref.update({'schedule': edited_df.to_dict('records')})
            write_log("Updated Schedule")
            st.success("Synced!")

    # Control Panel
    st.markdown('### 🛠️ MANUAL OVERRIDE')
    mode_remote = firebase_data.get('auto_mode', True)
    ctrl_1, ctrl_2, ctrl_3, ctrl_4 = st.columns(4)

    with ctrl_3:
        is_auto = st.toggle("Auto Mode", value=mode_remote)
        if is_auto != mode_remote:
            ref.update({'auto_mode': is_auto})
            write_log(f"Auto Mode: {is_auto}")

    with ctrl_1:
        if st.button("🔼 Open Valve", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_command_time': str(datetime.now())})
            write_log("Command: OPEN")

    with ctrl_2:
        if st.button("🔽 Close Valve", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_command_time': str(datetime.now())})
            write_log("Command: CLOSE")

    with ctrl_4:
        if st.button("🚨 EMERGENCY", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})
            write_log("EMERGENCY STOP")

    # Logs
    st.markdown("### 📜 ACTIVITY LOGS")
    try:
        logs = log_ref.order_by_key().limit_to_last(10).get()
        if logs:
            st.table(pd.DataFrame(list(logs.values())[::-1]))
    except: pass

    # Auto-refresh: รันเฉพาะเมื่อไม่มีการพิมพ์ข้อความ (ป้องกันหน้าเด้งขณะแก้ไขข้อมูล)
    time.sleep(2)
    st.rerun()

