import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import pytz
from datetime import datetime
import time

# --- 1. ตั้งค่าหน้ากระดานแบบ Simple (ช่วยเรื่องการ Render บน iOS) ---
st.set_page_config(page_title="GATE CONTROL", layout="centered") 

# --- 2. เชื่อมต่อ Firebase (ใช้ Secrets) ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error("Config Error")
        st.stop()

# อ้างอิง Node
ref = db.reference('valve_system')
local_tz = pytz.timezone('Asia/Bangkok')

# --- 3. ส่วนการแสดงผลที่ตัดฟีเจอร์หนักๆ ออกเพื่อ iOS รุ่นเก่า ---
st.markdown("<h2 style='text-align: center;'>🎛️ VALVE CONTROL</h2>", unsafe_allow_html=True)

# ดึงข้อมูลแบบ Static ก่อนเพื่อลดภาระเครื่อง
data = ref.get() or {}

# ใช้ Columns แบบง่ายๆ
col1, col2 = st.columns(2)
with col1:
    st.subheader("Pressure")
    st.write(f"### {data.get('live_pressure', 0.0):.2f} BAR")
with col2:
    st.subheader("Status")
    status = "AUTO" if data.get('auto_mode', True) else "MANUAL"
    st.write(f"### {status}")

st.divider()

# --- 4. ปุ่มกดขนาดใหญ่ (Touch Friendly) ---
if not data.get('auto_mode', True):
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔼 OPEN", use_container_width=True):
            ref.update({'command': 'OPEN'})
    with c2:
        if st.button("🔽 CLOSE", use_container_width=True):
            ref.update({'command': 'CLOSE'})
else:
    st.info("ระบบอยู่ในโหมดอัตโนมัติ")

if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
    ref.update({'command': 'STOP'})

# --- 5. จัดการการ Refresh (สำคัญมากสำหรับ iOS) ---
# แทนที่จะ rerun ทันที ให้ใช้ปุ่มแมนนวลหรือหน่วงเวลานานขึ้น
if st.button("🔄 Refresh Data"):
    st.rerun()

# หน่วงเวลา 10 วินาทีแทน 2 วินาที เพื่อไม่ให้ Safari รุ่นเก่าทำงานหนักเกินไป
time.sleep(10)
st.rerun()
