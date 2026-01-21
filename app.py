import streamlit as st

# --- 1. ตั้งค่าหน้ากระดาน (ต้องอยู่บรรทัดแรกสุดเสมอ) ---
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

# --- 2. การเชื่อมต่อ Firebase (ฉบับแก้ปัญหา Invalid Signature ขั้นสูงสุด) ---
if not firebase_admin._apps:
    try:
        # ดึงข้อมูลจาก st.secrets
        fb_dict = dict(st.secrets["firebase"])
        
        # ดึง Private Key ออกมา
        p_key = fb_dict["private_key"]
        
        # จัดการแปลงตัวอักษร \n ให้เป็นอักขระขึ้นบรรทัดใหม่จริงๆ 
        # และลบช่องว่างหัวท้ายที่อาจแฝงมา
        p_key = p_key.replace("\\n", "\n").strip()
        
        # ใส่กลับเข้าไปใน Dictionary
        fb_dict["private_key"] = p_key
        
        # สร้าง Credential และเชื่อมต่อ
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"❌ Firebase Auth Failed: {e}")
        st.stop()
        
# อ้างอิง Node หลักในฐานข้อมูล
ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 3. ฟังก์ชันการทำงานพื้นฐาน ---

def write_log(action):
    """บันทึกเหตุการณ์ลง Firebase"""
    try:
        log_ref.push({
            "user": st.session_state.get('username', 'Unknown'),
            "action": action,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except:
        pass

def init_default_user():
    """สร้างบัญชี Admin เริ่มต้นถ้ายังไม่มีในระบบ"""
    try:
        if user_ref.get() is None:
            user_ref.child('admin').set({
                'password': 'papak123',
                'role': 'super_admin'
            })
    except:
        pass

@st.cache_data(ttl=2)
def get_live_data():
    """ดึงข้อมูลจาก Firebase แบบ Real-time"""
    try:
        data = ref.get()
        if data:
            data['online'] = True
            return data
    except:
        pass
    return {
        'live_pressure': 0.0, 'valve_rotation': 0.0, 
        'auto_mode': True, 'motor_load': 0.0, 
        'schedule': [], 'online': False
    }

# --- 4. ระบบ Login ---

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        # ตกแต่งหน้า Login
        st.markdown("""
            <style>
            .login-box {
                background-color: rgba(30, 39, 46, 0.95);
                padding: 50px;
                border-radius: 20px;
                border: 2px solid #00ff88;
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
                text-align: center;
                margin-top: 50px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.title("🔐 GATE CONTROL")
            user_input = st.text_input("Username", key="input_u")
            pass_input = st.text_input("Password", type="password", key="input_p")
            
            if st.button("Login", use_container_width=True):
                if user_input:
                    try:
                        user_data = user_ref.child(user_input).get()
                        if user_data and user_data.get('password') == pass_input:
                            st.session_state.logged_in = True
                            st.session_state.username = user_input
                            write_log("เข้าสู่ระบบ")
                            st.rerun()
                        else:
                            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการตรวจสอบสิทธิ์: {e}")
                else:
                    st.warning("กรุณากรอก Username")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# --- 5. หน้า Dashboard หลัก ---

if check_login():
    init_default_user()
    data = get_live_data()

    # Sidebar
    st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        write_log("ออกจากระบบ")
        st.session_state.logged_in = False
        st.rerun()
    
    st.sidebar.divider()
    if data.get('online'):
        st.sidebar.success("● ระบบออนไลน์")
    else:
        st.sidebar.error("○ ระบบออฟไลน์")

    # CSS ตกแต่ง
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');
        .stApp { background: #0d0f12; color: #e0e0e0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; }
        .head-title { font-family: 'Orbitron'; color: #00ff88; text-shadow: 0 0 10px rgba(0,255,136,0.5); }
        .section-header { border-left: 5px solid #ff3e3e; padding-left: 10px; margin: 20px 0; font-family: 'Orbitron'; color: #ff3e3e; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="head-title">SYSTEM CONTROL VALVE PAPAK</h1>', unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("แรงดันขณะนี้", f"{data.get('live_pressure', 0.0):.2f} BAR")
    with m2: st.metric("รอบการหมุน", f"{data.get('valve_rotation', 0.0):.1f} REV")
    with m3: st.metric("โหลดมอเตอร์", f"{data.get('motor_load', 0.0)} A")
    with m4: st.metric("เวลาปัจจุบัน", datetime.now().strftime("%H:%M:%S"))

    # คอลัมน์กลาง
    c_left, c_right = st.columns([1.5, 1])
    with c_left:
        st.markdown('<div class="section-header">🚨 แรงดันย้อนหลัง</div>', unsafe_allow_html=True)
        if 'chart_data' not in st.session_state:
            t_idx = pd.date_range(end=datetime.now(), periods=24, freq='H')
            st.session_state.chart_data = pd.DataFrame({'Pressure': np.random.uniform(3.8, 4.2, 24)}, index=t_idx)
        st.line_chart(st.session_state.chart_data, color="#ff3e3e", height=250)

    with c_right:
        st.markdown('### 📋 ตารางทำงาน')
        sched_df = pd.DataFrame(data.get('schedule', [{"START_TIME": "08:00", "TARGET": 4.0}]))
        edited = st.data_editor(sched_df, use_container_width=True, num_rows="dynamic")
        if st.button("Apply Schedule"):
            ref.update({'schedule': edited.to_dict('records')})
            write_log("แก้ไขตารางทำงาน")
            st.success("บันทึกสำเร็จ!")

    # แผงควบคุม
    st.divider()
    st.markdown('### 🛠️ MANUAL OVERRIDE')
    is_auto = data.get('auto_mode', True)
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)

    with ctrl3:
        new_mode = st.toggle("Auto Mode", value=is_auto)
        if new_mode != is_auto:
            ref.update({'auto_mode': new_mode})
            write_log(f"โหมด: {'Auto' if new_mode else 'Manual'}")
            st.rerun()

    with ctrl1:
        if st.button("🔼 OPEN", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_cmd': str(datetime.now())})
            write_log("สั่งเปิดวาล์ว")

    with ctrl2:
        if st.button("🔽 CLOSE", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_cmd': str(datetime.now())})
            write_log("สั่งปิดวาล์ว")

    with ctrl4:
        if st.button("🚨 STOP", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})
            write_log("🚨 STOP!")

    # ประวัติ
    st.divider()
    st.markdown("### 📜 ประวัติการใช้งาน")
    try:
        logs = log_ref.order_by_key().limit_to_last(5).get()
        if logs:
            log_df = pd.DataFrame(list(logs.values())[::-1])
            st.table(log_df[['timestamp', 'user', 'action']])
    except:
        pass

    # หน่วงเวลา 3 วินาทีก่อนรีเฟรชข้อมูลเฉพาะตอน Login แล้ว
    time.sleep(3)
    st.rerun()


