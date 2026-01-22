import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 1. ตั้งค่าหน้ากระดาน (ตั้งเป็น collapsed เพื่อซ่อนตอนเริ่มต้น) ---
st.set_page_config(
    page_title="ระบบควบคุมประตูน้ำ น.นาแก",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. การเชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        p_key = fb_dict["private_key"].strip().replace("\\n", "\n")
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
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&display=swap');
            html, body, [class*="st-"], .stMarkdown, p, div {
                font-family: 'Noto Sans Thai', sans-serif !important;
            }
            .login-box {
                background-color: rgba(30, 39, 46, 0.95); padding: 50px; border-radius: 20px;
                border: 2px solid #00ff88; box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
                text-align: center; color: white;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.title("🔐 LOGIN")
            user_input = st.text_input("Username", key="input_u")
            pass_input = st.text_input("Password", type="password", key="input_p")
            if st.button("เข้าสู่ระบบ", use_container_width=True):
                user_data = user_ref.child(user_input).get()
                if user_data and user_data.get('password') == pass_input:
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    write_log("เข้าสู่ระบบ")
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# --- 5. Dashboard หลัก ---
if check_login():
    data = get_live_data()

    # --- CSS แก้ไขจุดบกพร่องเรื่อง Icon และ ปรับขนาด Sidebar ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Orbitron:wght@400;700&display=swap');
        
        /* 1. ตั้งค่าฟอนต์ไทยเฉพาะส่วนข้อความ ไม่รวม Icon */
        html, body, [data-testid="stHeader"], .stMarkdown, p, div, span, label {
            font-family: 'Noto Sans Thai', sans-serif !important;
        }

        /* 2. คืนค่าฟอนต์ไอคอนให้ระบบ Streamlit (ป้องกัน Keyboard_double_arrow...) */
        svg, i, [data-testid="stSidebarCollapseButton"] {
            font-family: inherit !important;
        }

        /* 3. ปรับ Sidebar ให้แคบลง 50% (เหลือประมาณ 150px) */
        [data-testid="stSidebar"] {
            width: 150px !important;
            min-width: 150px !important;
        }
        
        /* ลดขนาดตัวอักษรและระยะห่างใน Sidebar */
        [data-testid="stSidebar"] .stMarkdown p, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] label {
            font-size: 0.75rem !important;
            margin-bottom: 5px !important;
        }
        
        /* ปรับปุ่มใน Sidebar ให้เล็กลง */
        [data-testid="stSidebar"] button {
            height: 32px !important;
            font-size: 11px !important;
            padding: 2px 10px !important;
        }

        .stApp { background: #1e1f22; color: #efefef; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; font-size: 1.8rem !important; }
        .head-title { font-weight: 700; color: #00ff88; text-align: center; margin-bottom: 2rem; }

        /* ปรับแต่งปุ่มควบคุมหน้าหลัก */
        div.stButton > button { 
            height: 80px !important; 
            border-radius: 12px !important; 
            font-size: 18px !important; 
            font-weight: 700 !important; 
            background-color: #31333f !important; 
            color: white !important;
        }
        button[kind="primary"] { background-color: #dc2626 !important; }

        /* แก้ลูกศร Expander */
        [data-testid="stExpander"] details summary svg {
            float: right !important;
        }
        .streamlit-expanderHeader {
            background-color: #262730 !important;
            border-radius: 8px !important;
            padding-right: 40px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar (ข้อมูลขนาดเล็กพิเศษ)
    st.sidebar.markdown(f"👤 User: **{st.session_state.username}**")
    if st.sidebar.button("LOGOUT", use_container_width=True):
        write_log("ออกจากระบบ")
        st.session_state.logged_in = False
        st.rerun()
    st.sidebar.divider()
    if data['online']: st.sidebar.success("● ONLINE")
    else: st.sidebar.error("○ OFFLINE")

    # หน้าหลัก
    st.markdown('<h1 class="head-title">ระบบควบคุมประตูน้ำ น.ปลาปาก</h1>', unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("แรงดัน", f"{data.get('live_pressure', 0.0):.2f} Bar")
    with m2: st.metric("รอบหมุน", f"{data.get('valve_rotation', 0.0):.1f} รอบ")
    with m3: st.metric("โหลดมอเตอร์", f"{data.get('motor_load', 0.0)} A")
    with m4: st.metric("เวลาปัจจุบัน", datetime.now().strftime("%H:%M:%S"))

    # ส่วนควบคุม
    st.divider()
    is_auto = data.get('auto_mode', True)
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl3:
        new_mode = st.toggle("ระบบอัตโนมัติ (Auto)", value=is_auto)
        if new_mode != is_auto:
            ref.update({'auto_mode': new_mode})
            write_log(f"โหมด {new_mode}")
            st.rerun()

    with ctrl1:
        if st.button("🔼 OPEN\nเปิดวาล์ว", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_cmd': str(datetime.now())})
            write_log("สั่งเปิดวาล์ว")
    with ctrl2:
        if st.button("🔽 CLOSE\nปิดวาล์ว", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_cmd': str(datetime.now())})
            write_log("สั่งปิดวาล์ว")
    with ctrl4:
        if st.button("🚨 STOP\nหยุดฉุกเฉิน", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})
            write_log("🚨 สั่งหยุดฉุกเฉิน!")

    # ส่วนประวัติ
    st.divider()
    with st.expander("📊 ประวัติการใช้งานล่าสุด", expanded=False):
        try:
            logs = log_ref.order_by_key().limit_to_last(8).get()
            if logs:
                log_df = pd.DataFrame(list(logs.values())[::-1])
                st.table(log_df[['timestamp', 'user', 'action']])
            else:
                st.info("ยังไม่มีข้อมูลประวัติ")
        except:
            st.write("ไม่สามารถดึงข้อมูลประวัติได้")

    # Refresh
    time.sleep(3) 
    st.rerun()


