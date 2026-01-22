import streamlit as st

# --- 1. ตั้งค่าหน้ากระดาน (ต้องอยู่บรรทัดแรกสุดเสมอ) ---
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

# --- 2. การเชื่อมต่อ Firebase (ฉบับแก้ RefreshError) ---
if not firebase_admin._apps:
    try:
        # ดึงข้อมูลจาก st.secrets
        fb_dict = dict(st.secrets["firebase"])
        
        # ทำความสะอาดรหัส Private Key
        p_key = fb_dict["private_key"].strip()
        if "\\n" in p_key:
            p_key = p_key.replace("\\n", "\n")
        fb_dict["private_key"] = p_key
        
        # เริ่มต้นระบบ
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dbsensor-eb39d-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        st.error(f"⚠️ ไม่สามารถเชื่อมต่อ Firebase ได้: {e}")
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
        # ตกแต่งหน้า Login พร้อมปรับฟอนต์ Noto Sans Thai
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&display=swap');
            
            html, body, [class*="st-"], .stMarkdown, p, div {
                font-family: 'Noto Sans Thai', sans-serif !important;
            }

            .login-box {
                background-color: rgba(30, 39, 46, 0.95);
                padding: 50px;
                border-radius: 20px;
                border: 2px solid #00ff88;
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
                text-align: center;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.title("🔐 GATE CONTROL LOGIN")
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

# --- 5. หน้า Dashboard หลัก ---

if check_login():
    init_default_user()
    data = get_live_data()

    # แถบเมนูด้านข้าง
    st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: {st.session_state.username}")
    if st.sidebar.button("ออกจากระบบ", use_container_width=True):
        write_log("ออกจากระบบ")
        st.session_state.logged_in = False
        st.rerun()
    
    st.sidebar.divider()
    if data['online']:
        st.sidebar.success("● ระบบออนไลน์")
    else:
        st.sidebar.error("○ ระบบออฟไลน์")

    # --- ตกแต่ง UI ด้วย CSS (ฟอนต์ Gemini + สีปุ่ม + พื้นหลังสีเทา) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;700&family=Orbitron:wght@400;700&display=swap');
        
        /* 1. บังคับใช้ Noto Sans Thai ทั้งแอป */
        html, body, [class*="st-"], .stMarkdown, p, div, span, label {
            font-family: 'Noto Sans Thai', sans-serif !important;
        }

        /* 2. พื้นหลังแดชบอร์ดสีเทาเข้ม */
        .stApp { 
            background: #1e1f22; 
            color: #efefef; 
        }
        
        /* 3. ตกแต่ง Metric และหัวข้อ */
        [data-testid="stMetricValue"] { 
            font-family: 'Orbitron', sans-serif; 
            color: #00ff88 !important; 
            font-size: 2rem !important; 
        }
        .head-title { 
            font-weight: 700; 
            color: #00ff88; 
            text-align: center;
            text-shadow: 0 0 10px rgba(0,255,136,0.5); 
        }
        .section-header { 
            border-left: 5px solid #ff3e3e; 
            padding-left: 10px; 
            margin: 20px 0; 
            font-weight: 500; 
            color: #ff3e3e; 
        }

        /* 4. ปรับขนาดและสไตล์ปุ่มสั่งงาน */
        div.stButton > button {
            height: 90px !important;
            border-radius: 12px !important;
            font-size: 20px !important;
            font-weight: 700 !important;
            transition: all 0.3s ease;
        }

        /* 5. ปุ่ม OPEN - สีเขียวนีออน (Column 1) */
        div[data-testid="column"]:nth-child(1) button {
            background-color: #22c55e !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
        }

        /* 6. ปุ่ม CLOSE - สีเขียวเข้ม (Column 2) */
        div[data-testid="column"]:nth-child(2) button {
            background-color: #065f46 !important;
            color: white !important;
            border: none !important;
        }

        /* 7. ปุ่ม STOP - สีแดงสด (Primary Type) */
        button[kind="primary"] {
            background-color: #dc2626 !important;
            color: white !important;
            border: 2px solid white !important;
        }

        /* แก้ไขฟอนต์ในปุ่ม */
        button div p { font-family: 'Noto Sans Thai', sans-serif !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="head-title">ระบบควบคุมประตูน้ำ น.ปลาปาก</h1>', unsafe_allow_html=True)

    # แสดงผลค่า Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("แรงดันขณะนี้", f"{data.get('live_pressure', 0.0):.2f} BAR")
    with m2: st.metric("รอบการหมุน", f"{data.get('valve_rotation', 0.0):.1f} REV")
    with m3: st.metric("โหลดมอเตอร์", f"{data.get('motor_load', 0.0)} A")
    with m4: st.metric("เวลาปัจจุบัน", datetime.now().strftime("%H:%M:%S"))

    # ส่วนกลาง: กราฟและตั้งเวลา
    c_left, c_right = st.columns([1.5, 1])
    
    with c_left:
        st.markdown('<div class="section-header">🚨 แรงดันย้อนหลัง (3 วัน)</div>', unsafe_allow_html=True)
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
            write_log("แก้ไขตารางทำงาน")
            st.success("บันทึกสำเร็จ!")

    # ส่วนล่าง: แผงควบคุม Manual
    st.divider()
    st.markdown('### 🛠️ แผงควบคุมวาล์ว (MANUAL OVERRIDE)')
    
    is_auto = data.get('auto_mode', True)
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)

    with ctrl3:
        new_mode = st.toggle("โหมดอัตโนมัติ (Auto)", value=is_auto)
        if new_mode != is_auto:
            ref.update({'auto_mode': new_mode})
            write_log(f"เปลี่ยนโหมดเป็น {'Auto' if new_mode else 'Manual'}")
            st.rerun()

    with ctrl1:
        if st.button("🔼 เปิดวาล์ว\n(OPEN)", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'OPEN', 'last_cmd': str(datetime.now())})
            write_log("สั่งเปิดวาล์ว (Manual)")

    with ctrl2:
        if st.button("🔽 ปิดวาล์ว\n(CLOSE)", use_container_width=True, disabled=is_auto):
            ref.update({'command': 'CLOSE', 'last_cmd': str(datetime.now())})
            write_log("สั่งปิดวาล์ว (Manual)")

    with ctrl4:
        if st.button("🚨 หยุดฉุกเฉิน\n(STOP)", type="primary", use_container_width=True):
            ref.update({'command': 'STOP', 'emergency': True})
            write_log("🚨 สั่งหยุดฉุกเฉิน!")

    # ส่วนแสดงประวัติล่าสุด
    st.divider()
    st.markdown("### 📜 ประวัติการใช้งานล่าสุด")
    try:
        logs = log_ref.order_by_key().limit_to_last(8).get()
        if logs:
            log_df = pd.DataFrame(list(logs.values())[::-1])
            st.table(log_df[['timestamp', 'user', 'action']])
    except:
        st.info("ยังไม่มีข้อมูลประวัติ")

    # --- ส่วนการ Refresh หน้าจอ ---
    time.sleep(3) 
    st.rerun()
