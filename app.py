import streamlit as st

# --- 1. ตั้งค่าหน้ากระดาน (ต้องอยู่บรรทัดแรกสุดเสมอ) ---
st.set_page_config(
    page_title="ระบบควบคุมประตูน้ำ น.นาแก",
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

# --- 4. การตกแต่ง CSS (Noto Sans Thai แบบ Gemini) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Inter:wght@400;600&family=Orbitron:wght@500&display=swap');

    /* เปลี่ยนฟอนต์ทั้งแอปเป็น Noto Sans Thai */
    html, body, [class*="st-"] {
        font-family: 'Noto Sans Thai', sans-serif !important;
    }

    /* พื้นหลังโทนมืดแบบพรีเมียม */
    .stApp {
        background-color: #0f1113;
        color: #e3e3e3;
    }

    /* หัวข้อหน้าจอ */
    .head-title {
        font-weight: 700;
        color: #ffffff;
        text-align: center;
        padding-bottom: 20px;
        letter-spacing: 0.5px;
    }

    /* การตกแต่ง Metric */
    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', sans-serif !important;
        color: #00ff88 !important;
        font-size: 2.2rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        font-weight: 400 !important;
    }

    /* สไตล์ปุ่มกด */
    div.stButton > button {
        border-radius: 12px;
        font-weight: 500;
        height: 3.5em;
        transition: all 0.2s;
    }
    
    /* ปุ่มหยุดฉุกเฉิน */
    button[kind="primary"] {
        background-color: #ff4b4b !important;
        border: none !important;
    }

    /* กล่อง Header ส่วนต่างๆ */
    .section-header {
        border-left: 4px solid #00ff88;
        padding-left: 12px;
        margin: 25px 0 15px 0;
        font-weight: 600;
        color: #ffffff;
    }
    
    /* ปรับแต่งหน้า Login */
    .login-box {
        background-color: #1e1f20;
        padding: 40px;
        border-radius: 24px;
        border: 1px solid #333;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. ระบบ Login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.write("") # เว้นระยะข้างบน
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center; color:white; font-weight:700;">🔐 เข้าสู่ระบบ</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#888;">ระบบควบคุมประตูน้ำ น.ปลาปาก</p>', unsafe_allow_html=True)
        
        user_input = st.text_input("ชื่อผู้ใช้งาน (Username)")
        pass_input = st.text_input("รหัสผ่าน (Password)", type="password")
        
        if st.button("ตกลง", use_container_width=True):
            user_data = user_ref.child(user_input).get()
            if user_data and user_data.get('password') == pass_input:
                st.session_state.logged_in = True
                st.session_state.username = user_input
                write_log("เข้าสู่ระบบ")
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 6. หน้า Dashboard หลัก ---
data = get_live_data()

# Sidebar
st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: **{st.session_state.username}**")
if st.sidebar.button("ออกจากระบบ", use_container_width=True):
    write_log("ออกจากระบบ")
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.divider()
if data['online']:
    st.sidebar.success("● ระบบเชื่อมต่อออนไลน์")
else:
    st.sidebar.error("○ ระบบออฟไลน์")

# หัวข้อหลัก
st.markdown('<h1 class="head-title">GATE VALVE CONTROL SYSTEM</h1>', unsafe_allow_html=True)

# แถว Metrics (แสดงผลแรงดัน, รอบหมุน, โหลด)
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("แรงดันอากาศ", f"{data.get('live_pressure', 0.0):.2f} BAR")
with m2: st.metric("รอบหมุนวาล์ว", f"{data.get('valve_rotation', 0.0):.1f} REV")
with m3: st.metric("โหลดมอเตอร์", f"{data.get('motor_load', 0.0)} A")
with m4: st.metric("เวลาเซิร์ฟเวอร์", datetime.now().strftime("%H:%M:%S"))

st.divider()

# คอลัมน์กลาง
c_left, c_right = st.columns([1.6, 1])

with c_left:
    st.markdown('<div class="section-header">📈 สถิติแรงดันย้อนหลัง</div>', unsafe_allow_html=True)
    if 'chart_data' not in st.session_state:
        t_idx = pd.date_range(end=datetime.now(), periods=72, freq='H')
        st.session_state.chart_data = pd.DataFrame({'Pressure': np.random.uniform(3.8, 4.2, 72)}, index=t_idx)
    st.line_chart(st.session_state.chart_data, color="#00ff88", height=280)

with c_right:
    st.markdown('<div class="section-header">📋 ตารางการทำงาน</div>', unsafe_allow_html=True)
    sched_df = pd.DataFrame(data.get('schedule', [{"START_TIME": "08:00", "TARGET": 4.0}]))
    edited = st.data_editor(sched_df, use_container_width=True, num_rows="dynamic")
    if st.button("อัปเดตตารางเวลา", use_container_width=True):
        ref.update({'schedule': edited.to_dict('records')})
        write_log("แก้ไขตารางทำงาน")
        st.toast("บันทึกข้อมูลเรียบร้อยแล้ว!")

# แผงควบคุมวาล์ว
st.markdown('<div class="section-header">🕹️ แผงควบคุมระบบ (Manual Override)</div>', unsafe_allow_html=True)
is_auto = data.get('auto_mode', True)
ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)

with ctrl3:
    new_mode = st.toggle("เปิดโหมดอัตโนมัติ (Auto Mode)", value=is_auto)
    if new_mode != is_auto:
        ref.update({'auto_mode': new_mode})
        write_log(f"เปลี่ยนโหมดเป็น {'Auto' if new_mode else 'Manual'}")
        st.rerun()

with ctrl1:
    if st.button("🔼 สั่งเปิดวาล์ว", use_container_width=True, disabled=is_auto):
        ref.update({'command': 'OPEN', 'last_cmd': str(datetime.now())})
        write_log("สั่งเปิดวาล์ว")

with ctrl2:
    if st.button("🔽 สั่งปิดวาล์ว", use_container_width=True, disabled=is_auto):
        ref.update({'command': 'CLOSE', 'last_cmd': str(datetime.now())})
        write_log("สั่งปิดวาล์ว")

with ctrl4:
    if st.button("🚨 หยุดฉุกเฉิน (STOP)", type="primary", use_container_width=True):
        ref.update({'command': 'STOP', 'emergency': True})
        write_log("🚨 กดปุ่มหยุดฉุกเฉิน")

# ตารางประวัติ
st.divider()
st.markdown('<div class="section-header">📜 บันทึกกิจกรรมล่าสุด</div>', unsafe_allow_html=True)
try:
    logs = log_ref.order_by_key().limit_to_last(8).get()
    if logs:
        log_df = pd.DataFrame(list(logs.values())[::-1])
        st.dataframe(log_df[['timestamp', 'user', 'action']], use_container_width=True)
except:
    st.info("ไม่พบข้อมูลบันทึกกิจกรรม")

# หน่วงเวลา 3 วินาทีก่อน Refresh ข้อมูล
time.sleep(3)
st.rerun()
