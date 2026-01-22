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
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

# --- 2. การเชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        p_key = fb_dict["private_key"].replace("\\n", "\n").strip()
        fb_dict["private_key"] = p_key
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"❌ Firebase Error: {e}")
        st.stop()

ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 3. ฟังก์ชันการทำงาน ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except: pass

@st.cache_data(ttl=2)
def get_live_data():
    try:
        data = ref.get()
        if data: return data
    except: pass
    return {'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True, 'motor_load': 0.0}

# --- 4. CSS ปรับแต่ง UI สไตล์ Gemini + ปุ่มชัดเจน ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Inter:wght@400;700&display=swap');
    
    /* สไตล์ตัวอักษรและพื้นหลังแบบ Gemini */
    html, body, [class*="st-"] {
        font-family: 'Noto Sans Thai', 'Inter', sans-serif !important;
    }
    
    .stApp {
        background-color: #131314; /* Gemini Dark Background */
        color: #e3e3e3;
    }

    /* หัวข้อหน้าจอ */
    .head-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        color: #ffffff;
        text-align: center;
        padding: 30px 0;
        letter-spacing: 1px;
    }

    /* การ์ด Metric */
    div[data-testid="stMetric"] {
        background-color: #1e1f20;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #444746;
    }

    /* --- ปรับแต่งปุ่มสั่งงานให้ชัดเจนขึ้น --- */
    div.stButton > button {
        width: 100%;
        border-radius: 12px !important;
        height: 80px !important; /* เพิ่มความสูงปุ่ม */
        font-size: 20px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease;
        border: none !important;
        text-transform: uppercase;
    }

    /* ปุ่ม OPEN (สีเขียวนีออน) */
    div[data-testid="column"]:nth-child(1) button {
        background-color: #00d97e !important;
        color: #000000 !important;
        box-shadow: 0 4px 15px rgba(0, 217, 126, 0.4);
    }
    div[data-testid="column"]:nth-child(1) button:hover {
        background-color: #00ff95 !important;
        box-shadow: 0 0 25px rgba(0, 217, 126, 0.6);
    }

    /* ปุ่ม CLOSE (สีฟ้าสว่าง) */
    div[data-testid="column"]:nth-child(2) button {
        background-color: #007bff !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(0, 123, 255, 0.4);
    }
    div[data-testid="column"]:nth-child(2) button:hover {
        background-color: #3395ff !important;
        box-shadow: 0 0 25px rgba(0, 123, 255, 0.6);
    }

    /* ปุ่ม STOP (สีแดงเข้มข้น) */
    div[data-testid="column"]:nth-child(4) button {
        background-color: #ff3131 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 20px rgba(255, 49, 49, 0.5);
        border: 2px solid #ffffff !important;
    }
    div[data-testid="column"]:nth-child(4) button:hover {
        background-color: #ff5c5c !important;
        transform: scale(1.02);
    }
    
    /* ปุ่ม Toggle */
    .stCheckbox { font-size: 1.2rem; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

# --- 5. ระบบ Login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align: center;'>🔐 เข้าสู่ระบบควบคุม</h2>", unsafe_allow_html=True)
        u = st.text_input("ชื่อผู้ใช้")
        p = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            user_data = user_ref.child(u).get()
            if user_data and user_data.get('password') == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                write_log("Login")
                st.rerun()
            else: st.error("ข้อมูลไม่ถูกต้อง")
    st.stop()

# --- 6. Dashboard หน้าหลัก ---
data = get_live_data()

st.markdown('<h1 class="head-title">GATE VALVE MONITORING & CONTROL</h1>', unsafe_allow_html=True)

# Metrics แถวบน
m1, m2, m3, m4 = st.columns(4)
m1.metric("ความดันระบบ", f"{data.get('live_pressure', 0.0):.2f} BAR")
m2.metric("สถานะการเปิด", f"{data.get('valve_rotation', 0.0):.1f} REV")
m3.metric("กระแสไฟมอเตอร์", f"{data.get('motor_load', 0.0)} A")
m4.metric("เวลาอัปเดต", datetime.now().strftime("%H:%M:%S"))

st.divider()

# แผงควบคุม
st.subheader("🕹️ แผงควบคุม (Manual Override)")
is_auto = data.get('auto_mode', True)

# แสดงสถานะโหมดปัจจุบัน
if is_auto:
    st.info("💡 ขณะนี้อยู่ในโหมดอัตโนมัติ (ปุ่มแมนนวลถูกปิดใช้งาน)")
else:
    st.warning("⚠️ ขณะนี้อยู่ในโหมดแมนนวล (คุณสามารถสั่งการวาล์วได้โดยตรง)")

mode_toggle = st.toggle("เปิดใช้งานโหมดอัตโนมัติ (AUTO MODE)", value=is_auto)
if mode_toggle != is_auto:
    ref.update({'auto_mode': mode_toggle})
    write_log(f"โหมด: {'Auto' if mode_toggle else 'Manual'}")
    st.rerun()

st.write("") # เว้นวรรค

# ปุ่มกด (4 คอลัมน์)
ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)

with ctrl1:
    if st.button("🔼 เปิดวาล์ว\n(OPEN)", disabled=is_auto):
        ref.update({'command': 'OPEN'})
        write_log("สั่งเปิดวาล์ว")

with ctrl2:
    if st.button("🔽 ปิดวาล์ว\n(CLOSE)", disabled=is_auto):
        ref.update({'command': 'CLOSE'})
        write_log("สั่งปิดวาล์ว")

with ctrl3:
    # แสดงสถานะแบบข้อความชัดๆ ในช่องที่ 3
    status_text = "🟢 ระบบปกติ" if not data.get('emergency') else "🔴 หยุดฉุกเฉิน"
    st.markdown(f"<div style='text-align:center; padding-top:20px;'><h3>{status_text}</h3></div>", unsafe_allow_html=True)

with ctrl4:
    if st.button("🚨 หยุดทันที\n(STOP)"):
        ref.update({'command': 'STOP', 'emergency': True})
        write_log("EMERGENCY STOP")

st.divider()

# ตารางและกราฟ
c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("📜 บันทึกกิจกรรม 5 รายการล่าสุด")
    logs = log_ref.order_by_key().limit_to_last(5).get()
    if logs:
        st.table(pd.DataFrame(list(logs.values())[::-1])[['timestamp', 'action', 'user']])

with c2:
    st.subheader("⚙️ ตั้งค่าระบบ")
    if st.button("รีเซ็ตระบบ (Clear Emergency)"):
        ref.update({'emergency': False, 'command': 'IDLE'})
        st.success("รีเซ็ตสถานะฉุกเฉินแล้ว")

# รีเฟรชหน้าจอ
time.sleep(3)
st.rerun()
