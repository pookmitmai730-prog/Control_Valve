import streamlit as st
import pandas as pd
import numpy as np
import time
import pytz  # สำหรับจัดการเวลาประเทศไทย
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 0. ตั้งค่า Timezone ---
local_tz = pytz.timezone('Asia/Bangkok')

def get_now():
    """ดึงเวลาปัจจุบันเป็นเวลาไทย"""
    return datetime.now(local_tz)

# --- 1. ตั้งค่า Firebase (ปรับปรุงเพื่อรันบนเว็บ streamlit.io) ---
if not firebase_admin._apps:
    try:
        # ดึงข้อมูลจาก st.secrets แทนการเรียกไฟล์ตรงๆ
        fb_dict = dict(st.secrets["firebase"])
        # แก้ไขปัญหาเรื่องการขึ้นบรรทัดใหม่ในรหัส Private Key
        fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"❌ Firebase Connection Error: {e}")
        st.stop()

# อ้างอิง Node หลัก
ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 2. ฟังก์ชัน Initialize User ---
def init_default_user():
    try:
        users = user_ref.get()
        if users is None:
            user_ref.child('admin').set({
                'password': 'papak123',
                'role': 'super_admin'
            })
    except: pass

init_default_user()

# --- 3. ฟังก์ชันบันทึกประวัติ (ใช้เวลาไทย) ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": get_now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except: pass

# --- 4. ฟังก์ชันระบบ Login ---
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

# --- 5. ฟังก์ชันดึงข้อมูลแบบ Safety ---
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
# หมายเหตุ: st.set_page_config ต้องอยู่บรรทัดแรกๆ ของสคริปต์
st.set_page_config(page_title="GATE VALVE CONTROL", layout="wide")

if check_login():
    firebase_data = get_safe_data()
    now_th = get_now()

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
        div[data-testid="stVerticalBlock"] > div:has(div.stMetric) { background: rgba(30, 39, 46, 0.7); border-left: 4px solid #00ff88; padding: 15px; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; }
        .section-head-red { border-bottom: 1px solid #333; color: #ff3e3e; font-family: 'Orbitron'; font-size: 1.1rem; }
        .stButton>button { background: linear-gradient(135deg, #1e272e 0%, #2f3640 100%) !important; color: #00ff88 !important; border: 1px solid #00ff88 !important; font-family: 'Orbitron'; }
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-family:\'Orbitron\'; text-shadow: 0 0 10px #00ff88;">SYSTEM CONTROL VALVE PAPAK</h1>', unsafe_allow_html=True)

    # --- Metrics (แสดงเวลาไทย) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Live Pressure", f"{firebase_data.get('live_pressure', 0.0):.2f} BAR")
    with c2: st.metric("Valve Rotation", f"{firebase_data.get('valve_rotation', 0.0):.1f} REV")
    with c3: st.metric("Motor Load", f"{firebase_data.get('motor_load', 0.0)} A")
    with c4: st.metric("System Time (TH)", now_th.strftime("%H:%M:%S"))

    # --- Main Content ---
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown('<div class="section-head-red">🚨 PRESSURE TREND</div>', unsafe_allow_html=True)
        if 'history_df' not in st.session_state:
            # สร้างข้อมูลจำลองอิงตามเวลาไทย
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

    # --- Control Panel ---
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

    # --- Logs ---
    st.markdown("---")
    st.markdown("### 📜 RECENT ACTIVITY LOGS")
    try:
        logs = log_ref.order_by_key().limit_to_last(10).get()
        if logs:
            log_list = [logs[key] for key in reversed(logs.keys())]
            st.table(pd.DataFrame(log_list))
    except: pass

    time.sleep(5) # ปรับเวลา Refresh ให้เหมาะสมกับการรันบนเว็บ
    st.rerun()
