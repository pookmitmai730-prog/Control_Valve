import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 1. ตั้งค่าหน้ากระดาน ---
st.set_page_config(
    page_title="ระบบควบคุมประตูน้ำ น.นาแก",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. การเชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        p_key = fb_dict["private_key"].strip().replace("\\n", "\n")
        fb_dict["private_key"] = p_key
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'})
    except Exception as e:
        st.error(f"⚠️ ไม่สามารถเชื่อมต่อ Firebase ได้: {e}"); st.stop()

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
    return {'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True, 'motor_load': 0.0, 'schedule': [], 'online': False}

# --- 4. ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&display=swap');
            /* จำกัดฟอนต์เฉพาะในกล่อง Login */
            .login-box, .login-box input, .login-box button { font-family: 'Noto Sans Thai', sans-serif !important; }
            .login-box {
                background: rgba(30, 39, 46, 0.95); padding: 50px; border-radius: 20px;
                border: 2px solid #00ff88; text-align: center; color: white;
            }
            </style>
        """, unsafe_allow_html=True)
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.title("🔐 GATE CONTROL LOGIN")
            u = st.text_input("Username", key="input_u")
            p = st.text_input("Password", type="password", key="input_p")
            if st.button("เข้าสู่ระบบ", use_container_width=True):
                udata = user_ref.child(u).get()
                if udata and udata.get('password') == p:
                    st.session_state.logged_in = True; st.session_state.username = u
                    write_log("เข้าสู่ระบบ"); st.rerun()
                else: st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# --- 5. Dashboard หลัก ---
if check_login():
    data = get_live_data()

    # Sidebar
    st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: {st.session_state.username}")
    if st.sidebar.button("ออกจากระบบ", use_container_width=True):
        write_log("ออกจากระบบ"); st.session_state.logged_in = False; st.rerun()
    st.sidebar.divider()
    if data['online']: st.sidebar.success("● ระบบออนไลน์")
    else: st.sidebar.error("○ ระบบออฟไลน์")

    # --- CSS แก้ไขจุดบกพร่องเรื่อง Icon และ Expander ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Orbitron:wght@400;700&display=swap');
        
        /* แก้ปัญหา Keyboard_double_arrow: ห้ามใช้ฟอนต์ไทยทับ Material Icons */
        html, body, [class*="st-"] {
            font-family: 'Noto Sans Thai', sans-serif;
        }

        /* บังคับคืนค่าไอคอนของ Streamlit ไม่ให้โดน Noto Sans ทับ */
        .st-emotion-cache-1629671, [data-testid="stSidebarCollapseButton"] i, 
        [data-testid="stExpander"] svg, span[data-testid="stWidgetLabel"] p {
            font-family: inherit; /* ปล่อยให้ระบบจัดการฟอนต์ไอคอนเอง */
        }
        
        /* แก้ไขข้อความปุ่ม Sidebar หด (ถ้ายังขึ้นข้อความอยู่) */
        [data-testid="stSidebarCollapseButton"]::after { content: none !important; }

        .stApp { background: #1e1f22; color: #efefef; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; }
        .head-title { font-weight: 700; color: #00ff88; text-align: center; }

        /* ปุ่มและสี */
        div.stButton > button { height: 90px !important; border-radius: 12px !important; font-size: 20px !important; font-weight: 700 !important; background-color: #31333f !important; color: #ffffff !important; }
        button[kind="primary"] { background-color: #dc2626 !important; color: white !important; }

        /* แก้ลูกศร Expander ซ้อนทับ: ใช้ Padding ขวาเพื่อหลบลูกศรมาตรฐาน */
        .streamlit-expanderHeader { 
            background: #262730 !important; 
            border-radius: 10px !important; 
            padding-right: 50px !important; /* เว้นที่ให้ลูกศรฝั่งขวา */
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="head-title">ระบบควบคุมประตูน้ำ น.ปลาปาก</h1>', unsafe_allow_html=True)

    # --- Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("แรงดันขณะนี้", f"{data.get('live_pressure', 0.0):.2f} บาร์")
    with m2: st.metric("รอบการหมุน", f"{data.get('valve_rotation', 0.0):.1f} รอบ")
    with m3: st.metric("โหลดมอเตอร์", f"{data.get('motor_load', 0.0)} แอมป์")
    with m4: st.metric("เวลาปัจจุบัน", datetime.now().strftime("%H:%M:%S"))

    # --- กราฟและตาราง ---
    c_left, c_right = st.columns([1.5, 1])
    with c_left:
        st.markdown('### 🚨 แรงดันย้อนหลัง')
        if 'chart_data' not in st.session_state:
            t_idx = pd.date_range(end=datetime.now(), periods=72, freq='H')
            st.session_state.chart_data = pd.DataFrame({'Pressure': np.random.uniform(3.8, 4.2, 72)}, index=t_idx)
        st.line_chart(st.session_state.chart_data, color="#ff3e3e", height=250)

    with c_right:
        st.markdown('### 📋 ตารางการทำงาน')
        sched_df = pd.DataFrame(data.get('schedule', [{"START_TIME": "08:00", "TARGET": 4.0}]))
        edited = st.data_editor(sched_df, use_container_width=True, num_rows="dynamic")
        if st.button("บันทึกตารางใหม่", use_container_width=True):
            ref.update({'schedule': edited.to_dict('records')})
            write_log("แก้ไขตารางทำงาน"); st.success("บันทึกสำเร็จ!")

    # --- แผงควบคุม ---
    st.divider()
    st.markdown('### 🛠️ แผงควบคุมวาล์ว')
    is_auto = data.get('auto_mode', True)
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl3:
        new_mode = st.toggle("โหมดอัตโนมัติ (Auto)", value=is_auto)
        if new_mode != is_auto: ref.update({'auto_mode': new_mode}); write_log(f"โหมด {new_mode}"); st.rerun()

    with ctrl1:
        if st.button("🔼 OPEN", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_cmd': str(datetime.now())}); write_log("เปิดวาล์ว")
    with ctrl2:
        if st.button("🔽 CLOSE", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_cmd': str(datetime.now())}); write_log("ปิดวาล์ว")
    with ctrl4:
        if st.button("🚨 STOP", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True}); write_log("หยุดฉุกเฉิน")

    # --- ส่วนประวัติการใช้งาน ---
    st.divider()
    # ใช้ข้อความสั้นลงเพื่อลดโอกาสการทับซ้อน
    with st.expander("📊 ประวัติการใช้งาน 8 รายการล่าสุด", expanded=False):
        try:
            logs = log_ref.order_by_key().limit_to_last(8).get()
            if logs:
                log_df = pd.DataFrame(list(logs.values())[::-1])
                st.table(log_df[['timestamp', 'user', 'action']])
            else: st.info("ยังไม่มีข้อมูล")
        except: st.write("ไม่สามารถดึงข้อมูลได้")

    time.sleep(3); st.rerun()
