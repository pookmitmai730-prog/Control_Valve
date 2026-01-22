import streamlit as st

# --- 1. ตั้งค่าหน้ากระดาน ---
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
        st.error(f"⚠️ เชื่อมต่อ Firebase ล้มเหลว: {e}")
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
    except: pass

@st.cache_data(ttl=2)
def get_live_data():
    try:
        data = ref.get()
        if data:
            data['online'] = True
            return data
    except: pass
    return {'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True, 'motor_load': 0.0, 'online': False}

# --- 4. CSS ปรับเฉพาะฟอนต์ (Noto Sans Thai) แต่คงสีและสไตล์เดิม ---
st.markdown("""
    <style>
    /* ดึงฟอนต์ Noto Sans Thai สไตล์ Gemini */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Inter:wght@400;700&display=swap');

    /* บังคับใช้ฟอนต์ Noto Sans Thai ทั้งแอป */
    html, body, [class*="st-"], .stMarkdown, p, div {
        font-family: 'Noto Sans Thai', sans-serif !important;
    }

    /* พื้นหลังสีเทาเข้มแบบเดิม */
    .stApp {
        background-color: #1e1f22; 
        color: #efefef;
    }

    /* หัวข้อหน้าจอ */
    .head-title {
        color: #ffffff;
        text-align: center;
        padding: 20px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    /* การ์ด Metric สีเทาเข้ม */
    div[data-testid="stMetric"] {
        background-color: #2b2d31;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #3f4147;
    }
    [data-testid="stMetricValue"] {
        color: #00ff88 !important;
        font-weight: 700;
    }

    /* --- ปรับแต่งปุ่ม (สีตามที่คุณต้องการก่อนหน้านี้) --- */
    div.stButton > button {
        width: 100%;
        border-radius: 12px !important;
        height: 90px !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        border: none !important;
        font-family: 'Noto Sans Thai', sans-serif !important; /* ปุ่มก็ต้องเป็นฟอนต์นี้ */
    }

    /* ปุ่ม 1: OPEN (เขียวนีออน) */
    div[data-testid="column"]:nth-child(1) button {
        background-color: #22c55e !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
    }

    /* ปุ่ม 2: CLOSE (เขียวเข้ม) */
    div[data-testid="column"]:nth-child(2) button {
        background-color: #065f46 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(6, 95, 70, 0.3);
    }

    /* ปุ่ม 4: STOP (แดง) */
    div[data-testid="column"]:nth-child(4) button {
        background-color: #dc2626 !important;
        color: #ffffff !important;
        border: 2px solid #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. ระบบ Login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown('<div style="background-color:#2b2d31; padding:40px; border-radius:20px; border:1px solid #3f4147; margin-top:50px;">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center; color:white;">🔐 เข้าสู่ระบบ</h2>', unsafe_allow_html=True)
        u = st.text_input("ชื่อผู้ใช้งาน")
        p = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            user_data = user_ref.child(u).get()
            if user_data and user_data.get('password') == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                write_log("เข้าสู่ระบบ")
                st.rerun()
            else: st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 6. หน้า Dashboard ---
data = get_live_data()

st.markdown('<h1 class="head-title">ระบบควบคุมประตูน้ำ น.นาแก (ปลาปาก)</h1>', unsafe_allow_html=True)

# Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("แรงดัน (Pressure)", f"{data.get('live_pressure', 0.0):.2f} BAR")
m2.metric("การหมุน (Rotation)", f"{data.get('valve_rotation', 0.0):.1f} REV")
m3.metric("โหลด (Motor Load)", f"{data.get('motor_load', 0.0)} A")
m4.metric("สถานะออนไลน์", "ONLINE" if data.get('online') else "OFFLINE")

st.divider()

# แผงควบคุม
st.subheader("🕹️ แผงควบคุม (Manual Control)")
is_auto = data.get('auto_mode', True)
mode_toggle = st.toggle("เปิดใช้งานโหมดอัตโนมัติ (AUTO MODE)", value=is_auto)

if mode_toggle != is_auto:
    ref.update({'auto_mode': mode_toggle})
    write_log(f"เปลี่ยนโหมดเป็น {'Auto' if mode_toggle else 'Manual'}")
    st.rerun()

st.write("") 

# ปุ่มสีเขียว/เขียวเข้ม/แดง ตามสไตล์เดิม
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
    status_icon = "🟢" if not data.get('emergency') else "🔴"
    st.markdown(f"<div style='text-align:center; padding-top:20px;'><h3>{status_icon} ระบบทำงานปกติ</h3></div>", unsafe_allow_html=True)

with ctrl4:
    if st.button("🚨 หยุดทันที\n(STOP)"):
        ref.update({'command': 'STOP', 'emergency': True})
        write_log("🚨 สั่งหยุดฉุกเฉิน")

st.divider()

# ประวัติและกราฟ
c1, c2 = st.columns([1.5, 1])
with c1:
    st.subheader("📊 กราฟแรงดัน")
    st.line_chart(pd.DataFrame({'Pressure': np.random.uniform(3.9, 4.1, 24)}), color="#22c55e")

with c2:
    st.subheader("📜 ประวัติล่าสุด")
    try:
        logs = log_ref.order_by_key().limit_to_last(5).get()
        if logs:
            st.table(pd.DataFrame(list(logs.values())[::-1])[['timestamp', 'action']])
    except: st.write("ไม่มีข้อมูล")

time.sleep(2)
st.rerun()
