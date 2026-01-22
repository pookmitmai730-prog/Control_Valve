import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

# --- 1. ตั้งค่าหน้ากระดาน ---
st.set_page_config(
    page_title="GATE VALVE CONTROL SYSTEM",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. การเชื่อมต่อ Firebase (ผ่าน Secrets) ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n").strip()
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"❌ Firebase Error: {e}")
        st.stop()

ref = db.reference('valve_system')
log_ref = db.reference('activity_logs')

# --- 3. CSS ปรับแต่งสีเทาและปุ่มสีเขียว ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Inter:wght@400;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Noto Sans Thai', 'Inter', sans-serif !important;
    }
    
    /* พื้นหลังแดชบอร์ดสีเทาเข้ม */
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
        letter-spacing: 1px;
    }

    /* การ์ด Metric สีเทาอ่อนขึ้นมานิดนึง */
    div[data-testid="stMetric"] {
        background-color: #2b2d31;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #3f4147;
    }

    /* ปรับแต่งปุ่มสั่งงาน */
    div.stButton > button {
        width: 100%;
        border-radius: 12px !important;
        height: 90px !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease;
        border: none !important;
    }

    /* [ปุ่มที่ 1] OPEN - สีเขียวนีออนสว่าง */
    div[data-testid="column"]:nth-child(1) button {
        background-color: #22c55e !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
    }
    div[data-testid="column"]:nth-child(1) button:hover {
        background-color: #4ade80 !important;
        box-shadow: 0 0 25px rgba(34, 197, 94, 0.5);
    }

    /* [ปุ่มที่ 2] CLOSE - สีเขียวเข้ม Emerald */
    div[data-testid="column"]:nth-child(2) button {
        background-color: #065f46 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(6, 95, 70, 0.3);
    }
    div[data-testid="column"]:nth-child(2) button:hover {
        background-color: #047857 !important;
        box-shadow: 0 0 25px rgba(6, 95, 70, 0.5);
    }

    /* [ปุ่มที่ 4] STOP - สีแดงสด */
    div[data-testid="column"]:nth-child(4) button {
        background-color: #dc2626 !important;
        color: #ffffff !important;
        border: 2px solid #ffffff !important;
        box-shadow: 0 4px 20px rgba(220, 38, 38, 0.4);
    }

    /* ปรับแต่งตาราง */
    .stTable {
        background-color: #2b2d31;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. ฟังก์ชันบันทึก Log ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Admin'),
            "action": action,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except: pass

# --- 5. ดึงข้อมูล ---
@st.cache_data(ttl=1)
def get_data():
    try: return ref.get()
    except: return {}

data = get_data() or {}

# --- 6. แสดงผล Dashboard ---
st.markdown('<h1 class="head-title">GATE VALVE MONITORING DASHBOARD</h1>', unsafe_allow_html=True)

# แถว Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("แรงดัน (Pressure)", f"{data.get('live_pressure', 0.0):.2f} BAR")
m2.metric("การเปิด (Rotation)", f"{data.get('valve_rotation', 0.0):.1f} REV")
m3.metric("กระแส (Motor Load)", f"{data.get('motor_load', 0.0)} A")
m4.metric("เวลาปัจจุบัน", datetime.now().strftime("%H:%M:%S"))

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

# ปุ่มกดแบบสีเขียวตามที่ขอ
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
    # แสดงสถานะปัจจุบัน
    status = "🟢 ระบบปกติ" if not data.get('emergency') else "🔴 หยุดฉุกเฉิน"
    st.markdown(f"<div style='text-align:center; padding-top:25px;'><h3>{status}</h3></div>", unsafe_allow_html=True)

with ctrl4:
    if st.button("🚨 หยุดทันที\n(STOP)"):
        ref.update({'command': 'STOP', 'emergency': True})
        write_log("🚨 EMERGENCY STOP")

st.divider()

# ส่วนล่าง: กราฟและประวัติ
c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("📊 กราฟแรงดัน")
    chart_data = pd.DataFrame({'Pressure': np.random.uniform(3.9, 4.1, 20)})
    st.line_chart(chart_data, color="#22c55e")

with c2:
    st.subheader("📜 ประวัติการใช้งาน")
    try:
        logs = log_ref.order_by_key().limit_to_last(5).get()
        if logs:
            st.table(pd.DataFrame(list(logs.values())[::-1])[['timestamp', 'action']])
    except: st.write("ไม่มีข้อมูล")

# หน่วงเวลา 2 วินาทีแล้วรีเฟรช
time.sleep(2)
st.rerun()
