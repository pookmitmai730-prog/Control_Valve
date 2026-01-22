import streamlit as st

# --- 1. ตั้งค่าหน้ากระดาน (ต้องอยู่บรรทัดแรกสุดเสมอ) ---
st.set_page_config(
    page_title="ระบบควบคุมประตูน้ำ น.นาแก",
    layout="wide",
    initial_sidebar_state="collapsed"
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

# --- 3. ฟังก์ชันการทำงานพื้นฐาน ---
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
    return {'live_pressure': 0.0, 'valve_rotation': 0.0, 'auto_mode': True, 'motor_load': 0.0, 'schedule': [], 'online': False}

# --- 4. ระบบ Login ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&display=swap');
            html, body, [class*="st-"] { font-family: 'Noto Sans Thai', sans-serif !important; }
            .login-box {
                background-color: rgba(30, 39, 46, 0.95);
                padding: 40px; border-radius: 20px; border: 2px solid #00ff88;
                text-align: center; color: white; margin-top: 50px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col, _ = st.columns([0.5, 1, 0.5])
        with col:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.title("🔐 GATE CONTROL LOGIN")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("เข้าสู่ระบบ", use_container_width=True):
                user_data = user_ref.child(u).get()
                if user_data and user_data.get('password') == p:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    write_log("เข้าสู่ระบบ")
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# --- 5. หน้า Dashboard หลัก ---
if check_login():
    data = get_live_data()

    # --- ตกแต่ง UI ด้วย CSS ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Orbitron:wght@400;700&display=swap');
        
        /* บังคับซ่อน Sidebar */
        [data-testid="stSidebar"] { display: none; }
        
        html, body, [class*="st-"], .stMarkdown, p, div, span, label {
            font-family: 'Noto Sans Thai', sans-serif !important;
        }

        .stApp { background: #1e1f22; color: #efefef; }
        
        [data-testid="stMetricValue"] { 
            font-family: 'Orbitron', sans-serif; 
            color: #00ff88 !important; 
            font-size: 2rem !important; 
        }
        .head-title { 
            font-weight: 700; color: #00ff88; text-align: center;
            text-shadow: 0 0 10px rgba(0,255,136,0.5); 
        }

        /* ปุ่มพื้นฐาน (สีเทา) */
        div.stButton > button {
            height: 80px !important;
            border-radius: 12px !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            background-color: #31333f !important;
            color: #ffffff !important;
            border: 1px solid #464b5d !important;
            transition: all 0.3s ease !important;
        }

        /* Hover สีสำหรับแต่ละปุ่ม */
        .open-btn div.stButton > button:hover { background-color: #22c55e !important; border: none !important; }
        .close-btn div.stButton > button:hover { background-color: #065f46 !important; border: none !important; }
        .save-btn div.stButton > button:hover { background-color: #3b82f6 !important; border: none !important; }
        
        button[kind="primary"] { background-color: #dc2626 !important; color: white !important; border: 2px solid white !important; }
        button[kind="primary"]:hover { background-color: #ff0000 !important; }

        /* ปุ่ม Logout มุมขวา */
        .logout-btn button { height: 35px !important; font-size: 14px !important; border: 1px solid #ff4b4b !important; color: #ff4b4b !important; background: transparent !important;}
        .logout-btn button:hover { background: #ff4b4b !important; color: white !important; }

        /* แก้ไข Expander ซ้อนทับ */
        .streamlit-expanderHeader { 
            gap: 15px !important; 
            font-size: 1.1rem !important; 
            font-weight: 600 !important; 
        }
        .streamlit-expanderHeader p { margin: 0 !important; line-height: 1.5 !important; }

        [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 1.1rem !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- Top Bar (Status & User) ---
    t_left, t_center, t_right = st.columns([1, 2, 1])
    with t_left:
        st.write("● ออนไลน์" if data['online'] else "○ ออฟไลน์", "🟢" if data['online'] else "🔴")
    with t_center:
        st.markdown('<h1 class="head-title">ระบบควบคุมประตูน้ำ น.ปลาปาก</h1>', unsafe_allow_html=True)
    with t_right:
        r1, r2 = st.columns([1.5, 1])
        r1.markdown(f"<div style='text-align: right; padding-top: 5px;'>👤 <b>{st.session_state.username}</b></div>", unsafe_allow_html=True)
        with r2:
            st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
            if st.button("Logout", key="btn_logout"):
                st.session_state.logged_in = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # --- Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("แรงดันขณะนี้", f"{data.get('live_pressure', 0.0):.2f} บาร์")
    m2.metric("รอบการหมุน", f"{data.get('valve_rotation', 0.0):.1f} รอบ")
    m3.metric("โหลดมอเตอร์", f"{data.get('motor_load', 0.0)} A")
    m4.metric("เวลาเซิร์ฟเวอร์", datetime.now().strftime("%H:%M:%S"))

    # --- Middle Section (Graph & Schedule) ---
    c_left, c_right = st.columns([1.5, 1])
    with c_left:
        st.markdown('### 🚨 แรงดันย้อนหลัง')
        chart_data = pd.DataFrame({'Pressure': np.random.uniform(3.8, 4.2, 24)}) # ตัวอย่างข้อมูล
        st.line_chart(chart_data, color="#ff3e3e", height=230)

    with c_right:
        st.markdown('### 📋 ตารางทำงาน')
        sched_df = pd.DataFrame(data.get('schedule', [{"START_TIME": "08:00", "TARGET": 4.0}]))
        edited = st.data_editor(sched_df, use_container_width=True, num_rows="dynamic")
        st.markdown('<div class="save-btn">', unsafe_allow_html=True)
        if st.button("💾 บันทึกตารางใหม่", use_container_width=True):
            ref.update({'schedule': edited.to_dict('records')})
            write_log("แก้ไขตารางทำงาน")
            st.success("บันทึกสำเร็จ!")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Control Panel ---
    st.divider()
    st.markdown('### 🛠️ แผงควบคุมวาล์ว (MANUAL OVERRIDE)')
    is_auto = data.get('auto_mode', True)
    
    # แบ่งเป็น 2 แถว แถวละ 2 ปุ่ม เพื่อให้ดูในมือถือได้ง่าย
    ctrl_row1_col1, ctrl_row1_col2 = st.columns(2)
    ctrl_row2_col1, ctrl_row2_col2 = st.columns(2)

    with ctrl_row1_col1:
        st.markdown('<div class="open-btn">', unsafe_allow_html=True)
        if st.button("🔼 เปิดวาล์ว (OPEN)", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_cmd': str(datetime.now())})
            write_log("สั่งเปิดวาล์ว")
        st.markdown('</div>', unsafe_allow_html=True)

    with ctrl_row1_col2:
        st.markdown('<div class="close-btn">', unsafe_allow_html=True)
        if st.button("🔽 ปิดวาล์ว (CLOSE)", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_cmd': str(datetime.now())})
            write_log("สั่งปิดวาล์ว")
        st.markdown('</div>', unsafe_allow_html=True)

    with ctrl_row2_col1:
        new_mode = st.toggle("เปิดใช้งานโหมดอัตโนมัติ (Auto Mode)", value=is_auto)
        if new_mode != is_auto:
            ref.update({'auto_mode': new_mode})
            write_log(f"เปลี่ยนโหมดเป็น {'Auto' if new_mode else 'Manual'}")
            st.rerun()

    with ctrl_row2_col2:
        if st.button("🚨 หยุดฉุกเฉิน (STOP)", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})
            write_log("🚨 สั่งหยุดฉุกเฉิน!")

    # --- Logs ---
    st.divider()
    with st.expander("📊 คลิกเพื่อดูประวัติการใช้งานล่าสุด", expanded=False):
        try:
            logs = log_ref.order_by_key().limit_to_last(5).get()
            if logs:
                log_df = pd.DataFrame(list(logs.values())[::-1])
                st.table(log_df[['timestamp', 'user', 'action']])
            else:
                st.info("ยังไม่มีข้อมูลประวัติ")
        except:
            st.write("เชื่อมต่อฐานข้อมูลไม่ได้")

    time.sleep(3)
    st.rerun()
