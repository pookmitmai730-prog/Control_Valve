import streamlit as st

# --- 1. ตั้งค่าหน้ากระดาน ---
st.set_page_config(
    page_title="ระบบควบคุมประตูน้ำ น.นาแก",
    layout="wide",
    initial_sidebar_state="collapsed"
)

import pandas as pd
import numpy as np
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

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

@st.cache_data(ttl=2)
def get_live_data():
    try:
        data = ref.get()
        if data:
            data['online'] = True
            return data
    except:
        pass
    return {'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True, 'motor_load': 0.0, 'schedule': [], 'online': False}

# --- 4. ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&display=swap');
            html, body, [class*="st-"] { font-family: 'Noto Sans Thai', sans-serif !important; }
            .login-box {
                background-color: rgba(30, 39, 46, 0.95);
                padding: 30px; border-radius: 20px; border: 2px solid #00ff88;
                text-align: center; color: white; margin-top: 50px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col, _ = st.columns([0.2, 1, 0.2]) # ปรับคอลัมน์ให้กว้างขึ้นในมือถือ
        with col:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.title("🔐 LOGIN")
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            if st.button("เข้าสู่ระบบ", use_container_width=True):
                user_data = user_ref.child(user_input).get()
                if user_data and user_data.get('password') == pass_input:
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    write_log("เข้าสู่ระบบ")
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# --- 5. Dashboard ---
if check_login():
    data = get_live_data()

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;700&family=Orbitron:wght@700&display=swap');
        [data-testid="stSidebar"] { display: none; }
        html, body, [class*="st-"] { font-family: 'Noto Sans Thai', sans-serif !important; }
        .stApp { background: #1e1f22; color: #efefef; }
        
        /* Metric Styling */
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; font-size: 1.8rem !important; }
        [data-testid="stMetricLabel"] { color: #ffffff !important; }
        
        .head-title { font-weight: 700; color: #00ff88; text-align: center; font-size: 1.5rem; text-shadow: 0 0 10px rgba(0,255,136,0.3); }

        /* Button Styling */
        div.stButton > button {
            height: 70px !important; /* ลดความสูงลงเล็กน้อยให้พอดีมือถือ */
            border-radius: 12px !important;
            font-size: 18px !important;
            background-color: #31333f !important;
            transition: all 0.3s;
        }
        
        /* Hover Colors */
        div.open-btn button:hover { background-color: #22c55e !important; box-shadow: 0 0 15px rgba(34, 197, 94, 0.4); }
        div.close-btn button:hover { background-color: #065f46 !important; }
        div.save-btn button:hover { background-color: #3b82f6 !important; }
        
        button[kind="primary"] { background-color: #dc2626 !important; border: 2px solid white !important; }
        
        .logout-btn button { height: 35px !important; font-size: 14px !important; border: 1px solid #ff4b4b !important; color: #ff4b4b !important; }
        </style>
    """, unsafe_allow_html=True)

    # Header Section
    t_left, t_right = st.columns([1, 1])
    with t_left:
        st.write("● ออนไลน์" if data['online'] else "○ ออฟไลน์", "🟢" if data['online'] else "🔴")
    with t_right:
        st.markdown(f"<div style='text-align: right;'>👤 <b>{st.session_state.username}</b></div>", unsafe_allow_html=True)
        if st.button("Logout", key="out", use_container_width=False):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown('<h1 class="head-title">ระบบควบคุมประตูน้ำ น.ปลาปาก</h1>', unsafe_allow_html=True)

    # Metrics (Auto-wrap in mobile)
    m1, m2 = st.columns(2)
    m1.metric("แรงดัน", f"{data.get('live_pressure', 0.0):.2f} บาร์")
    m2.metric("รอบหมุน", f"{data.get('valve_rotation', 0.0):.1f} รอบ")
    
    m3, m4 = st.columns(2)
    m3.metric("โหลด", f"{data.get('motor_load', 0.0)} A")
    m4.metric("เวลา", datetime.now().strftime("%H:%M"))

    # Controls - ปรับเป็น 2x2 สำหรับมือถือ
    st.divider()
    st.markdown("### 🛠️ การควบคุม")
    is_auto = data.get('auto_mode', True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="open-btn">', unsafe_allow_html=True)
        if st.button("🔼 OPEN", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN'})
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="close-btn">', unsafe_allow_html=True)
        if st.button("🔽 CLOSE", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE'})
        st.markdown('</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        new_mode = st.toggle("โหมดอัตโนมัติ", value=is_auto)
        if new_mode != is_auto:
            ref.update({'auto_mode': new_mode})
            st.rerun()
    with col4:
        if st.button("🚨 STOP", type="primary", use_container_width=True):
            ref.update({'command': 'STOP'})

    # Logs Section (Expander)
    st.divider()
    with st.expander("📊 ดูประวัติย้อนหลัง"):
        try:
            logs = log_ref.order_by_key().limit_to_last(5).get()
            if logs:
                st.table(pd.DataFrame(list(logs.values())[::-1])[['timestamp', 'action']])
        except: st.write("ไม่มีข้อมูล")

    time.sleep(3)
    st.rerun()
