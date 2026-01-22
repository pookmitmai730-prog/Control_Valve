import streamlit as st

# --- 1. ตั้งค่าหน้ากระดาน ---
st.set_page_config(
    page_title="GATE VALVE CONTROL SYSTEM",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 2. การเชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        p_key = fb_dict["private_key"]
        p_key = p_key.replace("\\n", "\n").strip()
        fb_dict["private_key"] = p_key
        
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"❌ Firebase Auth Failed: {e}")
        st.stop()

ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 3. ฟังก์ชันพื้นฐาน ---
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
    return {'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True, 'motor_load': 0.0, 'online': False}

# --- 4. ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun&display=swap');
            .login-box {
                background-color: #1e2124;
                padding: 40px;
                border-radius: 15px;
                border: 1px solid #00ff88;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                text-align: center;
                font-family: 'Sarabun', sans-serif;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.title("🔐 เข้าสู่ระบบ")
            user_input = st.text_input("ชื่อผู้ใช้งาน")
            pass_input = st.text_input("รหัสผ่าน", type="password")
            if st.button("ตกลง", use_container_width=True):
                user_data = user_ref.child(user_input).get()
                if user_data and user_data.get('password') == pass_input:
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    write_log("เข้าสู่ระบบ")
                    st.rerun()
                else:
                    st.error("ข้อมูลไม่ถูกต้อง")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# --- 5. Dashboard หลัก ---
if check_login():
    data = get_live_data()

    # CSS ตกแต่ง Dashboard (Font Sarabun + ปรับปรุงปุ่ม)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Sarabun:wght@300;400;700&display=swap');
        
        /* พื้นหลังดำอ่อน */
        .stApp { 
            background-color: #161b22; 
            color: #e6edf3; 
            font-family: 'Sarabun', sans-serif; 
        }
        
        /* หัวข้อไฮเทค */
        .head-title { 
            font-family: 'Orbitron'; 
            color: #00ff88; 
            text-align: center;
            padding: 20px;
            background: rgba(0,255,136,0.05);
            border-radius: 10px;
            margin-bottom: 25px;
        }

        /* ปรับแต่ง Metric */
        [data-testid="stMetricValue"] { font-family: 'Orbitron'; color: #00ff88 !important; }

        /* ปรับแต่งปุ่มคำสั่ง (Custom Buttons) */
        div.stButton > button {
            border-radius: 10px;
            height: 3em;
            transition: all 0.3s ease;
            font-family: 'Sarabun', sans-serif;
            font-weight: bold;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        /* ปุ่ม Open (สีเขียว) */
        div[data-testid="column"]:nth-child(1) button {
            background-color: #1d332a !important;
            color: #00ff88 !important;
            border: 1px solid #00ff88 !important;
        }
        div[data-testid="column"]:nth-child(1) button:hover {
            box-shadow: 0 0 15px rgba(0,255,136,0.4);
            transform: translateY(-2px);
        }

        /* ปุ่ม Close (สีฟ้า/ส้ม) */
        div[data-testid="column"]:nth-child(2) button {
            background-color: #21262d !important;
            color: #58a6ff !important;
            border: 1px solid #58a6ff !important;
        }
        div[data-testid="column"]:nth-child(2) button:hover {
            box-shadow: 0 0 15px rgba(88,166,255,0.4);
        }

        /* ปุ่ม STOP (สีแดงกระพริบนิดๆ) */
        div[data-testid="column"]:nth-child(4) button {
            background-color: #3d1b1b !important;
            color: #ff4d4d !important;
            border: 2px solid #ff4d4d !important;
            text-transform: uppercase;
        }
        div[data-testid="column"]:nth-child(4) button:hover {
            background-color: #ff4d4d !important;
            color: white !important;
            box-shadow: 0 0 20px rgba(255,77,77,0.6);
        }
        
        /* ตกแต่งตาราง */
        .stDataFrame { background: #0d1117; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="head-title">⚙️ SYSTEM CONTROL VALVE PAPAK</h1>', unsafe_allow_html=True)

    # Sidebar
    st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: **{st.session_state.username}**")
    if st.sidebar.button("Log out"):
        st.session_state.logged_in = False
        st.rerun()
    st.sidebar.divider()
    if data.get('online'):
        st.sidebar.success("● ระบบเชื่อมต่อออนไลน์")
    else:
        st.sidebar.error("○ ขาดการเชื่อมต่อ")

    # ส่วนแสดงผลหลัก
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("แรงดันอากาศ", f"{data.get('live_pressure', 0.0):.2f} BAR")
    col2.metric("การเปิดวาล์ว", f"{data.get('valve_rotation', 0.0):.1f} %")
    col3.metric("กระแสมอเตอร์", f"{data.get('motor_load', 0.0)} A")
    col4.metric("เวลาเซิร์ฟเวอร์", datetime.now().strftime("%H:%M"))

    st.divider()

    # กราฟและตาราง
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.subheader("📊 แนวโน้มแรงดัน (Real-time)")
        if 'chart_data' not in st.session_state:
            st.session_state.chart_data = pd.DataFrame({'Pressure': [data.get('live_pressure', 0.0)]})
        st.line_chart(st.session_state.chart_data, color="#00ff88", height=250)

    with c2:
        st.subheader("📋 ตั้งเวลาทำงาน")
        sched_df = pd.DataFrame(data.get('schedule', [{"TIME": "08:00", "SET": 4.0}]))
        edited = st.data_editor(sched_df, use_container_width=True, num_rows="dynamic")
        if st.button("Update Schedule"):
            ref.update({'schedule': edited.to_dict('records')})
            st.success("บันทึกตารางแล้ว")

    # แผงควบคุม (Modern Style)
    st.markdown("### 🕹️ แผงควบคุมการสั่งงาน")
    is_auto = data.get('auto_mode', True)
    
    # ใช้ Toggle สวยๆ
    new_mode = st.toggle("เปิดใช้งานโหมดอัตโนมัติ (Auto Mode)", value=is_auto)
    if new_mode != is_auto:
        ref.update({'auto_mode': new_mode})
        write_log(f"เปลี่ยนเป็นโหมด {'Auto' if new_mode else 'Manual'}")
        st.rerun()

    # ปุ่มคำสั่ง 4 ปุ่ม
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl1:
        if st.button("🔼 OPEN VALVE", use_container_width=True, disabled=new_mode):
            ref.update({'command': 'OPEN', 'last_cmd_time': str(datetime.now())})
            write_log("สั่งเปิดวาล์ว")
    with ctrl2:
        if st.button("🔽 CLOSE VALVE", use_container_width=True, disabled=new_mode):
            ref.update({'command': 'CLOSE', 'last_cmd_time': str(datetime.now())})
            write_log("สั่งปิดวาล์ว")
    with ctrl3:
        st.info("Manual Mode" if not new_mode else "Auto Running...")
    with ctrl4:
        if st.button("🚨 EMERGENCY STOP", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})
            write_log("🚨 กดหยุดฉุกเฉิน!")

    # ประวัติล่าสุด
    with st.expander("📜 ดูประวัติการสั่งงานล่าสุด"):
        try:
            logs = log_ref.order_by_key().limit_to_last(10).get()
            if logs:
                st.table(pd.DataFrame(list(logs.values())[::-1]))
        except:
            st.write("ยังไม่มีข้อมูล")

    time.sleep(3)
    st.rerun()
