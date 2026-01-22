import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 1. ตั้งค่าหน้ากระดาน (ต้องอยู่บรรทัดแรก) ---
st.set_page_config(
    page_title="GATE VALVE CONTROL SYSTEM",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. การเชื่อมต่อ Firebase (ผ่าน Secrets) ---
if not firebase_admin._apps:
    try:
        # อ่านค่าจาก Secrets ของ Streamlit Cloud
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n").strip()
        
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"❌ Firebase Config Error: {e}")
        st.stop()

# อ้างอิง Node
ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 3. ฟังก์ชันการทำงานพื้นฐาน ---
def write_log(action):
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": datetime.now().strftime("%H:%M:%S | %d-%m-%Y")
        })
    except: pass

def init_default_user():
    try:
        if user_ref.get() is None:
            user_ref.child('admin').set({'password': 'papak123', 'role': 'super_admin'})
    except: pass

@st.cache_data(ttl=2)
def get_safe_data():
    try:
        data = ref.get()
        if data:
            data['online'] = True
            return data
    except: pass
    return {'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True, 'motor_load': 0.0, 'online': False}

# --- 4. สไตล์ CSS (Gemini Dark Theme + Ultra-Clear Buttons) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Inter:wght@400;700&display=swap');
    
    /* พื้นหลังและฟอนต์หลัก */
    html, body, [class*="st-"] {
        font-family: 'Noto Sans Thai', 'Inter', sans-serif !important;
    }
    .stApp { background-color: #0f1113; color: #e3e3e3; }

    /* การ์ด Metric */
    div[data-testid="stMetric"] {
        background-color: #1a1c1e;
        padding: 20px; border-radius: 12px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricValue"] { color: #00ff88 !important; font-weight: 700; }

    /* ปุ่มควบคุมขนาดใหญ่และชัดเจน */
    div.stButton > button {
        height: 100px !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        border-radius: 15px !important;
        border: none !important;
        transition: 0.3s;
    }

    /* ปุ่ม OPEN (สีเขียวสว่าง) */
    div[data-testid="column"]:nth-child(1) button {
        background: linear-gradient(135deg, #00c853 0%, #00e676 100%) !important;
        color: #000 !important;
        box-shadow: 0 0 20px rgba(0, 230, 118, 0.3);
    }

    /* ปุ่ม CLOSE (สีน้ำเงินสว่าง) */
    div[data-testid="column"]:nth-child(2) button {
        background: linear-gradient(135deg, #2979ff 0%, #448aff 100%) !important;
        color: #fff !important;
        box-shadow: 0 0 20px rgba(41, 121, 255, 0.3);
    }

    /* ปุ่ม STOP (สีแดงสด) */
    div[data-testid="column"]:nth-child(4) button {
        background: #ff1744 !important;
        color: #fff !important;
        border: 3px solid #fff !important;
        box-shadow: 0 0 30px rgba(255, 23, 68, 0.5);
    }
    
    .status-card {
        background: #1a1c1e; padding: 15px; border-radius: 12px;
        text-align: center; border: 1px solid #333;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. ระบบ Login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, login_col, _ = st.columns([1, 1, 1])
    with login_col:
        st.markdown("<h2 style='text-align:center;'>🔐 เข้าสู่ระบบควบคุม</h2>", unsafe_allow_html=True)
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            init_default_user()
            user_data = user_ref.child(u).get()
            if user_data and user_data.get('password') == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                write_log("เข้าสู่ระบบ")
                st.rerun()
            else: st.error("❌ ข้อมูลไม่ถูกต้อง")
    st.stop()

# --- 6. เนื้อหา Dashboard หลัก ---
data = get_safe_data()

# Header
st.markdown("<h1 style='text-align:center; color:#fff;'>GATE VALVE SMART MONITORING</h1>", unsafe_allow_html=True)

# แถวบน: Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("แรงดันอากาศ (Pressure)", f"{data.get('live_pressure', 0.0):.2f} BAR")
m2.metric("การเปิดวาล์ว (Rotation)", f"{data.get('valve_rotation', 0.0):.1f} REV")
m3.metric("โหลดมอเตอร์ (Load)", f"{data.get('motor_load', 0.0)} A")
m4.metric("สถานะระบบ", "ONLINE" if data.get('online') else "OFFLINE")

st.divider()

# แถวกลาง: กราฟและตาราง
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📊 กราฟแรงดันย้อนหลัง")
    if 'history_df' not in st.session_state:
        st.session_state.history_df = pd.DataFrame({'Pressure': np.random.uniform(3.8, 4.2, 20)})
    st.line_chart(st.session_state.history_df, color="#00ff88", height=250)

with col_right:
    st.subheader("📋 ตารางเวลาทำงาน (Schedule)")
    sched_raw = data.get('schedule', [{"START": "08:00", "TARGET": 4.0}])
    edited_df = st.data_editor(pd.DataFrame(sched_raw), use_container_width=True, num_rows="dynamic")
    if st.button("บันทึกตารางเวลา", use_container_width=True):
        ref.update({'schedule': edited_df.to_dict('records')})
        write_log("แก้ไขตารางเวลา")
        st.success("บันทึกสำเร็จ!")

st.divider()

# แถวล่าง: แผงควบคุม (Manual Override)
st.subheader("🕹️ แผงควบคุมสั่งการ (Manual Override)")
is_auto = data.get('auto_mode', True)

mode_toggle = st.toggle("เปิดใช้งานโหมดอัตโนมัติ (AUTO MODE)", value=is_auto)
if mode_toggle != is_auto:
    ref.update({'auto_mode': mode_toggle})
    write_log(f"เปลี่ยนโหมดเป็น {'Auto' if mode_toggle else 'Manual'}")
    st.rerun()

st.write("") # Spacer

btn1, btn2, btn3, btn4 = st.columns(4)

with btn1:
    if st.button("🔼 เปิดวาล์ว\n(OPEN)", use_container_width=True, disabled=is_auto):
        ref.update({'command': 'OPEN'})
        write_log("สั่งเปิดวาล์ว")

with btn2:
    if st.button("🔽 ปิดวาล์ว\n(CLOSE)", use_container_width=True, disabled=is_auto):
        ref.update({'command': 'CLOSE'})
        write_log("สั่งปิดวาล์ว")

with btn3:
    status_color = "#00ff88" if not data.get('emergency') else "#ff1744"
    st.markdown(f"""
        <div class="status-card">
            <h4 style="margin:0; color:{status_color};">สถานะปัจจุบัน</h4>
            <h2 style="margin:0;">{'ปกติ' if not data.get('emergency') else 'หยุดฉุกเฉิน'}</h2>
        </div>
    """, unsafe_allow_html=True)

with btn4:
    if st.button("🚨 หยุดทันที\n(STOP)", use_container_width=True):
        ref.update({'command': 'STOP', 'emergency': True})
        write_log("🚨 EMERGENCY STOP!")

# ประวัติล่าสุด
st.divider()
with st.expander("📜 ดูบันทึกเหตุการณ์ล่าสุด"):
    try:
        logs = log_ref.order_by_key().limit_to_last(10).get()
        if logs:
            st.table(pd.DataFrame(list(logs.values())[::-1]))
    except: st.write("ไม่มีข้อมูล")

# หน่วงเวลาและรีเฟรช
time.sleep(2)
st.rerun()
