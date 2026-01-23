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
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;700&display=swap');
            html, body, [class*="st-"] { font-family: 'Noto Sans Thai', sans-serif; }
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

    # --- CSS STYLING (FIX: Fonts, Metric Colors & Arrows) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;600;700&family=Orbitron:wght@400;700&family=Rajdhani:wght@400;600;700&display=swap');
        
        /* 1. คืนค่าไอคอนลูกศร (SVG) และสัญลักษณ์ระบบให้เป็นกราฟิกปกติ */
        svg, [data-testid="stSidebarNav"] svg, [data-testid="collapsedControl"] svg {
            display: inline-block !important;
            fill: currentColor !important;
            color: inherit !important;
        }

        /* 2. Global Fonts (จัดลำดับเพื่อไม่ให้ทับ Emoji และ Icon ระบบ) */
        html, body, .stMarkdown p, .stMarkdown span, label {
            font-family: 'Rajdhani', 'Noto Sans Thai', sans-serif !important;
        }

        /* 3. ปรับแต่งหัวข้อ Metric ให้เป็นสีขาวเข้มคมชัด (Pure White) */
        [data-testid="stMetricLabel"] p {
            color: #FFFFFF !important;
            font-family: 'Noto Sans Thai', sans-serif !important;
            font-size: 1.15rem !important;
            font-weight: 600 !important;
            opacity: 1 !important;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        }

        /* 4. ปรับแต่งตัวเลข Metric (สีเขียวนีออน) */
        [data-testid="stMetricValue"] {
            color: #00ff88 !important;
            font-family: 'Orbitron', sans-serif !important;
        }

        /* 5. Sidebar: ตัวหนังสือสีดำ และฟอนต์ไทย */
        [data-testid="stSidebar"] .stMarkdown p, 
        [data-testid="stSidebar"] .stMarkdown span,
        [data-testid="stSidebar"] strong {
            color: #000000 !important;
            font-family: 'Noto Sans Thai', sans-serif !important;
        }
        
        /* แก้สีลูกศรใน Sidebar ให้ชัดเจน */
        [data-testid="stSidebar"] button[kind="header"] {
            color: #000000 !important;
        }

        /* 6. ปุ่มควบคุม (องรับ Emoji 🔼 🔽 🚨) */
        .stButton>button { 
            background: linear-gradient(135deg, #1e272e 0%, #2f3640 100%) !important; 
            color: #00ff88 !important; 
            border: 1px solid #00ff88 !important; 
            font-family: 'Segoe UI Emoji', 'Orbitron', 'Noto Sans Thai', sans-serif !important; 
        }

        /* Theme พื้นหลัง */
        .stApp { background: radial-gradient(circle, #1a1f25 0%, #0d0f12 100%); color: #e0e0e0; }
        [data-testid="stSidebar"] a { color: #000000 !important; text-decoration: underline; font-weight: bold; }
        .section-head-red { border-bottom: 1px solid #333; color: #ff3e3e; font-family: 'Orbitron', 'Noto Sans Thai'; font-size: 1.1rem; margin-bottom: 10px;}
        </style>
        """, unsafe_allow_html=True)

    # --- SIDEBAR & LINKS ---
    st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: {st.session_state.username}")
    
    if not firebase_data['online']:
        st.sidebar.warning("⚠️ โหมดออฟไลน์ (Offline)")
    else:
        st.sidebar.success("● ระบบออนไลน์ (Online)")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("🔗 **ลิงก์ข้อมูลเพิ่มเติม**")
    st.sidebar.markdown("- [ข้อมูลถังน้ำใสเรณู](https://water-aimonitor-leak.onrender.com/showWater)")
    st.sidebar.markdown("- [ข้อมูล P3 นาป่งครอง น.นาแก](https://water-aimonitor-leak.onrender.com/)")
    st.sidebar.markdown("---")

    if st.sidebar.button("ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # --- MAIN CONTENT ---
    st.markdown('<h1 style="font-family:\'Orbitron\', \'Noto Sans Thai\'; text-shadow: 0 0 10px #00ff88;">ระบบควบคุมประตูน้ำ น.ปลาปาก</h1>', unsafe_allow_html=True)

    # --- 5. DASHBOARD METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("แรงดันขณะนี้", f"{firebase_data.get('live_pressure', 0.0):.2f} บาร์")
    with m2: st.metric("รอบการหมุนวาล์ว", f"{firebase_data.get('valve_rotation', 0.0):.1f} รอบ")
    with m3: st.metric("ภาระโหลดมอเตอร์", f"{firebase_data.get('motor_load', 0.0)} แอมป์")
    with m4: st.metric("เวลาปัจจุบัน (ไทย)", now_th.strftime("%H:%M:%S"))

    # Content Columns
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown('<div class="section-head-red">🚨 PRESSURE TREND (แนวโน้มแรงดัน)</div>', unsafe_allow_html=True)
        if 'history_df' not in st.session_state:
            time_index = pd.date_range(start=now_th-timedelta(days=3), end=now_th, freq='1H')
            st.session_state.history_df = pd.DataFrame({'Pressure': np.random.uniform(3.5, 4.5, size=len(time_index))}, index=time_index)
        st.line_chart(st.session_state.history_df, color="#ff3e3e", height=250)

    with col_right:
        st.markdown('### 📋 SCHEDULE SETTING (ตั้งค่าเวลา)')
        schedule_raw = firebase_data.get('schedule', [{"START_TIME": "00:00", "TARGET": 0.0}])
        current_schedule = pd.DataFrame(schedule_raw)
        edited_df = st.data_editor(current_schedule, use_container_width=True, num_rows="dynamic")
        
        if st.button("Apply & Sync to Firebase", use_container_width=True):
            try:
                ref.update({'schedule': edited_df.to_dict('records')})
                write_log("Updated Schedule Configuration")
                st.success("✅ บันทึกข้อมูลสำเร็จ!")
            except:
                st.error("❌ บันทึกล้มเหลว!")

    # Manual Control Panel
    st.markdown('### 🛠️ MANUAL OVERRIDE (ควบคุมด้วยตนเอง)')
    mode_remote = firebase_data.get('auto_mode', True)
    ctrl_1, ctrl_2, ctrl_3, ctrl_4 = st.columns([1, 1, 1, 1])

    with ctrl_3:
        is_auto = st.toggle("Auto Mode (โหมดอัตโนมัติ)", value=mode_remote)
        if is_auto != mode_remote:
            try:
                ref.update({'auto_mode': is_auto})
                write_log(f"Auto Mode set to {is_auto}")
            except: pass

    with ctrl_1:
        if st.button("🔼 Open Valve (เปิด)", use_container_width=True, disabled=is_auto):
            try:
                ref.update({'command': 'OPEN', 'last_command_time': now_th.strftime("%Y-%m-%d %H:%M:%S")})
                write_log("Manual Command: OPEN")
            except: pass

    with ctrl_2:
        if st.button("🔽 Close Valve (ปิด)", use_container_width=True, disabled=is_auto):
            try:
                ref.update({'command': 'CLOSE', 'last_command_time': now_th.strftime("%Y-%m-%d %H:%M:%S")})
                write_log("Manual Command: CLOSE")
            except: pass

    with ctrl_4:
        if st.button("🚨 Emergency Stop (หยุด)", type="primary", use_container_width=True):
            try:
                ref.update({'command': 'STOP', 'emergency': True})
                write_log("EMERGENCY STOP")
                st.error("ส่งคำสั่งหยุดฉุกเฉินแล้ว")
            except: pass

    # Activity Logs
    st.markdown("---")
    st.markdown("### 📜 RECENT ACTIVITY LOGS (ประวัติกิจกรรม)")
    try:
        logs = log_ref.order_by_key().limit_to_last(10).get()
        if logs:
            log_list = [logs[key] for key in reversed(logs.keys())]
            st.table(pd.DataFrame(log_list))
    except: pass

    # Auto Refresh System
    time.sleep(5) 
    st.rerun()
