import streamlit as st
import pandas as pd
import numpy as np
import time
import pytz
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 0. SETTINGS & TIMEZONE ---
local_tz = pytz.timezone('Asia/Bangkok')

def get_now():
    """ดึงเวลาปัจจุบันเป็นเวลาไทย"""
    return datetime.now(local_tz)

# --- 1. FIREBASE INITIALIZATION ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"❌ Firebase Connection Error: {e}")
        st.stop()

# Database References
ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 2. HELPER FUNCTIONS ---
def init_default_user():
    try:
        if user_ref.get() is None:
            user_ref.child('admin').set({'password': 'papak123', 'role': 'super_admin'})
    except: pass

def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": get_now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except: pass

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

# --- 3. LOGIN SYSTEM ---
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
                margin-top: 50px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col2, _ = st.columns([1, 1.2, 1])
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

# --- 4. MAIN INTERFACE ---
st.set_page_config(page_title="GATE VALVE CONTROL", layout="wide")
init_default_user()

if check_login():
    firebase_data = get_safe_data()
    now_th = get_now()

    # --- SIDEBAR & LINKS ---
    st.sidebar.markdown(f"### 👤 User: {st.session_state.username}")
    
    if not firebase_data['online']:
        st.sidebar.warning("⚠️ Offline Mode")
    else:
        st.sidebar.success("● System Online")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("🔗 **ลิงก์ข้อมูลเพิ่มเติม**")
    st.sidebar.markdown("- [ข้อมูลถังน้ำใสเรณู](https://water-aimonitor-leak.onrender.com/showWater)")
    st.sidebar.markdown("- [ข้อมูล P3 นาป่งครอง น.นาแก](https://water-aimonitor-leak.onrender.com/)")
    st.sidebar.markdown("---")

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # --- CSS STYLING (GLOBAL) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle, #1a1f25 0%, #0d0f12 100%); color: #e0e0e0; font-family: 'Rajdhani', sans-serif; }
        
        /* Sidebar Links Neon Style */
        [data-testid="stSidebar"] a { color: #00ff88 !important; text-decoration: none; font-weight: bold; }
        [data-testid="stSidebar"] a:hover { text-shadow: 0 0 10px #00ff88; }
        
        /* Metric Styling */
        div[data-testid="stVerticalBlock"] > div:has(div.stMetric) { background: rgba(30, 39, 46, 0.7); border-left: 4px solid #00ff88; padding: 15px; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; }
        
        /* Section Headers */
        .section-head-red { border-bottom: 1px solid #333; color: #ff3e3e; font-family: 'Orbitron'; font-size: 1.1rem; margin-bottom: 10px;}
        
        /* Button Styling */
        .stButton>button { background: linear-gradient(135deg, #1e272e 0%, #2f3640 100%) !important; color: #00ff88 !important; border: 1px solid #00ff88 !important; font-family: 'Orbitron'; }
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-family:\'Orbitron\'; text-shadow: 0 0 10px #00ff88;">SYSTEM CONTROL VALVE PAPAK</h1>', unsafe_allow_html=True)

    # --- 5. DASHBOARD METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Live Pressure", f"{firebase_data.get('live_pressure', 0.0):.2f} BAR")
    with m2: st.metric("Valve Rotation", f"{firebase_data.get('valve_rotation', 0.0):.1f} REV")
    with m3: st.metric("Motor Load", f"{firebase_data.get('motor_load', 0.0)} A")
    with m4: st.metric("System Time (TH)", now_th.strftime("%H:%M:%S"))

    # --- 6. DATA VISUALIZATION & SCHEDULE ---
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown('<div class="section-head-red">🚨 PRESSURE TREND</div>', unsafe_allow_html=True)
        if 'history_df' not in st.session_state:
            time_index = pd.date_range(start=now_th-timedelta(days=3), end=now_th, freq='1H')
            st.session_state.history_df = pd.DataFrame({'Pressure': np.random.uniform(3.5, 4.5, size=len(time_index))}, index=time_index)
        st.line_chart(st.session_state.history_df, color="#ff3e3e", height=250)

    with col_right:
        st.markdown('### 📋 SCHEDULE SETTING')
        schedule_raw = firebase_data.get('schedule', [{"START_TIME": "00:00", "TARGET": 0.0}])
        current_schedule = pd.DataFrame(schedule_raw)
        edited_df = st.data_editor(current_schedule, use_container_width=True, num_rows="dynamic")
        
        if st.button("Apply & Sync to Firebase", use_container_width=True):
            try:
                ref.update({'schedule': edited_df.to_dict('records')})
                write_log("Updated Schedule Configuration")
                st.success("✅ Synced & Logged!")
            except:
                st.error("❌ Sync Failed!")

    # --- 7. MANUAL CONTROL PANEL ---
    st.markdown('### 🛠️ MANUAL OVERRIDE')
    mode_remote = firebase_data.get('auto_mode', True)
    ctrl_1, ctrl_2, ctrl_3, ctrl_4 = st.columns([1, 1, 1, 1])

    with ctrl_3:
        is_auto = st.toggle("Auto Mode", value=mode_remote)
        if is_auto != mode_remote:
            try:
                ref.update({'auto_mode': is_auto})
                write_log(f"Auto Mode set to {is_auto}")
            except: pass

    with ctrl_1:
        if st.button("🔼 Open Valve", use_container_width=True, disabled=is_auto):
            try:
                ref.update({'command': 'OPEN', 'last_command_time': now_th.strftime("%Y-%m-%d %H:%M:%S")})
                write_log("Manual Command: OPEN")
            except: pass

    with ctrl_2:
        if st.button("🔽 Close Valve", use_container_width=True, disabled=is_auto):
            try:
                ref.update({'command': 'CLOSE', 'last_command_time': now_th.strftime("%Y-%m-%d %H:%M:%S")})
                write_log("Manual Command: CLOSE")
            except: pass

    with ctrl_4:
        if st.button("🚨 Emergency Stop", type="primary", use_container_width=True):
            try:
                ref.update({'command': 'STOP', 'emergency': True})
                write_log("EMERGENCY STOP")
                st.error("STOP SENT")
            except: pass

    # --- 8. ACTIVITY LOGS ---
    st.markdown("---")
    st.markdown("### 📜 RECENT ACTIVITY LOGS")
    try:
        logs = log_ref.order_by_key().limit_to_last(10).get()
        if logs:
            log_list = [logs[key] for key in reversed(logs.keys())]
            st.table(pd.DataFrame(log_list))
    except: pass

    # --- 9. AUTO REFRESH ---
    time.sleep(5) 
    st.rerun()
