import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db

# --- 1. ตั้งค่าหน้ากระดาน (เปลี่ยนเป็น collapsed เพื่อซ่อนตอนเริ่มต้น) ---
st.set_page_config(
    page_title="ระบบควบคุมประตูน้ำ น.นาแก",
    layout="wide",
    initial_sidebar_state="collapsed"  # สถานะเริ่มต้นเป็น Hidden
)

# --- 2. การเชื่อมต่อ Firebase (เหมือนเดิม) ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        p_key = fb_dict["private_key"].strip().replace("\\n", "\n")
        fb_dict["private_key"] = p_key
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'})
    except Exception as e:
        st.error(f"⚠️ Firebase Error: {e}"); st.stop()

ref = db.reference('valve_system')
user_ref = db.reference('valve_system/users')
log_ref = db.reference('activity_logs')

# --- 3. ฟังก์ชันพื้นฐาน (เหมือนเดิม) ---
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

# --- 4. ระบบ Login (เหมือนเดิม) ---
def check_login():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&display=swap');
            html, body, [class*="st-"], p, div { font-family: 'Noto Sans Thai', sans-serif !important; }
            .login-box {
                background: rgba(30, 39, 46, 0.95); padding: 50px; border-radius: 20px;
                border: 2px solid #00ff88; text-align: center; color: white;
            }
            </style>
        """, unsafe_allow_html=True)
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.title("🔐 LOGIN")
            u = st.text_input("Username", key="input_u")
            p = st.text_input("Password", type="password", key="input_p")
            if st.button("เข้าสู่ระบบ", use_container_width=True):
                udata = user_ref.child(u).get()
                if udata and udata.get('password') == p:
                    st.session_state.logged_in = True; st.session_state.username = u
                    write_log("เข้าสู่ระบบ"); st.rerun()
                else: st.error("ข้อมูลไม่ถูกต้อง")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# --- 5. Dashboard หลัก ---
if check_login():
    data = get_live_data()

    # --- CSS แก้ไขจุดบกพร่อง และ ปรับ SIDEBAR ให้แคบพิเศษ ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Orbitron:wght@400;700&display=swap');
        
        html, body, [class*="st-"], .stMarkdown, p, div, span, label {
            font-family: 'Noto Sans Thai', sans-serif !important;
        }

        /* แก้ไขไอคอน Sidebar ที่กลายเป็นตัวหนังสือ Keyboard_double... */
        [data-testid="stSidebarCollapseButton"] svg, 
        [data-testid="stExpander"] svg,
        .material-icons, i {
            font-family: 'inherit' !important;
        }

        /* --- ปรับ Sidebar แคบลง 50% จากเดิม (ประมาณ 130px) --- */
        [data-testid="stSidebar"] {
            width: 130px !important;
            min-width: 130px !important;
        }
        [data-testid="stSidebar"] .stMarkdown p, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] label {
            font-size: 0.7rem !important;
            line-height: 1.2 !important;
        }
        [data-testid="stSidebar"] button {
            height: 30px !important;
            font-size: 11px !important;
        }

        .stApp { background: #1e1f22; color: #efefef; }
        [data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #00ff88 !important; font-size: 1.8rem !important; }
        .head-title { font-weight: 700; color: #00ff88; text-align: center; }

        /* ปุ่มแผงควบคุมหลัก */
        div.stButton > button { height: 80px !important; border-radius: 12px !important; font-size: 18px !important; font-weight: 700 !important; background-color: #31333f !important; }
        button[kind="primary"] { background-color: #dc2626 !important; color: white !important; }

        /* แก้ลูกศร Expander ซ้อนทับ */
        [data-testid="stExpander"] details summary svg { float: right !important; }
        .streamlit-expanderHeader { 
            background: #262730 !important; 
            border-radius: 10px !important; 
            padding-right: 40px !important; 
        }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar (ข้อมูลขนาดเล็กพิเศษ)
    st.sidebar.markdown(f"👤 **{st.session_state.username}**")
    if st.sidebar.button("LOGOUT", use_container_width=True):
        write_log("ออกจากระบบ"); st.session_state.logged_in = False; st.rerun()
    st.sidebar.divider()
    if data['online']: st.sidebar.success("ON")
    else: st.sidebar.error("OFF")

    # ส่วนหน้าหลัก
    st.markdown('<h1 class="head-title">ระบบควบคุมประตูน้ำ น.ปลาปาก</h1>', unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("แรงดัน", f"{data.get('live_pressure', 0.0):.2f} Bar")
    with m2: st.metric("รอบหมุน", f"{data.get('valve_rotation', 0.0):.1f} รอบ")
    with m3: st.metric("โหลด", f"{data.get('motor_load', 0.0)} A")
    with m4: st.metric("เวลา", datetime.now().strftime("%H:%M:%S"))

    # ส่วนควบคุม
    st.divider()
    is_auto = data.get('auto_mode', True)
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl3:
        new_mode = st.toggle("Auto Mode", value=is_auto)
        if new_mode != is_auto: ref.update({'auto_mode': new_mode}); st.rerun()

    with ctrl1:
        if st.button("🔼 OPEN", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_cmd': str(datetime.now())})
    with ctrl2:
        if st.button("🔽 CLOSE", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_cmd': str(datetime.now())})
    with ctrl4:
        if st.button("🚨 STOP", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})

    # ส่วนประวัติ
    st.divider()
    with st.expander("📊 ประวัติการใช้งาน", expanded=False):
        try:
            logs = log_ref.order_by_key().limit_to_last(8).get()
            if logs:
                log_df = pd.DataFrame(list(logs.values())[::-1])
                st.table(log_df[['timestamp', 'user', 'action']])
        except: st.write("Error")

    time.sleep(3); st.rerun()
