import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import os

# --- 1. 설정 및 비밀번호 관리 ---
COMPANY_NAME = "프라임시티"
JSON_FILE = 'service_account.json' 
BUILDING_LIST = ["더빌", "엘리트타워", "장안프라임광교", "장안프라임광교2", "S타워", "킹덤부띠크"]

# [비밀번호 설정]
SITE_PASSWORD = "5922"      # 현장 전용 링크용 (공통)
ADMIN_PASSWORD = "7258"    # 메인 주소 접속용 (관리자)

scope = [
    "https://www.googleapis.com/auth/spreadsheets", 
    "https://www.googleapis.com/auth/drive"
]

# --- 2. 화면 설정 및 파라미터 읽기 ---
st.set_page_config(page_title=f"{COMPANY_NAME} 통합검침", layout="centered")

# [어르신 맞춤형 왕버튼 및 왕글씨 스타일]
st.markdown("""
    <style>
    /* 전체 글자 크기 키우기 */
    html, body, [class*="css"] {
        font-size: 24px !important;
    }
    /* 입력창 높이 및 글자 크기 3배 수준 확대 */
    input {
        height: 80px !important;
        font-size: 35px !important;
        font-weight: bold !important;
    }
    /* 버튼 크기, 글자 크기 확대 및 모서리 곡률 조정 */
    button {
        height: 100px !important;
        font-size: 40px !important; /* 글자 크기를 30px에서 40px로 확대 */
        font-weight: bold !important;
        background-color: #2e86de !important;
        color: white !important;
        border-radius: 20px !important; /* 모서리를 더 둥글게 */
    }
    /* 라벨(항목명) 크기 확대 */
    .stMarkdown p, .stMarkdown h3 {
        font-size: 32px !important;
        font-weight: bold !important;
    }
    /* 선택 박스 크기 확대 */
    div[data-baseweb="select"] {
        height: 80px !important;
        font-size: 28px !important;
    }
    </style>
""", unsafe_allow_html=True)

# 주소창 파라미터 읽기
url_params = st.query_params
url_building = url_params.get("b", None)

# --- 3. 보안 인증 로직 ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    if url_building in BUILDING_LIST:
        target_pwd = SITE_PASSWORD
        header_msg = f"🔒 {url_building} 인증"
    else:
        target_pwd = ADMIN_PASSWORD
        header_msg = f"🔒 {COMPANY_NAME} 관리자"

    st.markdown(f"### {header_msg}")
    input_pwd = st.text_input("비밀번호 입력", type="password", key="auth_pwd")
    
    if st.button("접속하기 (여기를 누르세요)"):
        if input_pwd == target_pwd:
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# --- 4. 구글 시트 연결 ---
@st.cache_resource
def get_gspread_client():
    try:
        if os.path.exists(JSON_FILE):
            creds = Credentials.from_service_account_file(JSON_FILE, scopes=scope)
        else:
            info = dict(st.secrets["gcp_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ 연결 오류 발생: {e}")
        return None

client = get_gspread_client()
if client:
    try:
        spreadsheet = client.open("검침데이터_관리")
    except Exception as e:
        st.error(f"⚠️ 시트 열기 실패: {e}")
        st.stop()
else:
    st.stop()

# --- 5. 화면 디자인 로직 ---
if not url_building:
    st.markdown(f"""
        <div style='text-align: center; background-color: #1c2833; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
            <h1 style='color: #ecf0f1; margin: 0; font-size: 45px;'>{COMPANY_NAME}</h1>
            <p style='color: #95a5a6; margin: 5px 0 0 0; font-size: 25px;'>통합 검침 관리</p>
        </div>
        """, unsafe_allow_html=True)

if url_building in BUILDING_LIST:
    selected_building = url_building
    st.markdown(f"""
        <div style='background-color: #d4edda; padding: 20px; border-radius: 10px; border: 3px solid #28a745; text-align: center; margin-bottom: 25px;'>
            <h2 style='color: #155724; margin: 0; font-size: 40px;'>🏢 {selected_building}</h2>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("### 🏗️ 현장 선택")
    selected_building = st.selectbox("현장을 골라주세요", ["선택하세요"] + BUILDING_LIST, label_visibility="collapsed")
    if selected_building == "선택하세요":
        st.info("현장을 먼저 선택해 주세요.")
        st.stop()

# 워크시트 로드
try:
    sheet = spreadsheet.worksheet(selected_building)
except gspread.exceptions.WorksheetNotFound:
    sheet = spreadsheet.add_worksheet(title=selected_building, rows="1000", cols="10")
    sheet.append_row(["일시", "건물명", "호수", "전기", "수도", "난방", "온수", "냉방"])

def get_last_reading(target_sheet, room_number):
    try:
        data = target_sheet.get_all_records()
        if not data: return None
        df = pd.DataFrame(data)
        filtered_df = df[df['호수'].astype(str) == str(room_number)]
        return filtered_df.iloc[-1] if not filtered_df.empty else None
    except: return None

def safe_float(val):
    try:
        if val is None or val == "" or str(val).isspace(): return 0.0
        return float(val)
    except: return 0.0

st.divider()

# --- 6. 호수 입력 및 데이터 조회 ---
st.markdown(f"### 🔢 {selected_building} 호수 입력")
if 'room_input' not in st.session_state:
    st.session_state['room_input'] = ""

room = st.text_input("여기에 호수를 입력하세요", value=st.session_state['room_input'], placeholder="예: 101", key="main_room_input")
load_btn = st.button("1. 데이터 찾기 🔍", use_container_width=True)

# 조회 로직
if load_btn or (room and st.session_state.get('last_room') != room):
    st.session_state['last_room'] = room
    st.session_state['room_input'] = room
    last_data = get_last_reading(sheet, room)
    st.session_state['last_data'] = last_data
    
    if last_data is not None:
        st.success(f"📊 {room}호 과거 기록을 찾았습니다.")
        st.markdown("""
            <style>
            .reading-container { display: flex; flex-direction: column; background-color: #262730; padding: 20px; border-radius: 10px; gap: 10px; border: 1px solid #444; }
            .reading-box { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #333; }
            .reading-label { color: #f1c40f; font-size: 28px; font-weight: bold; }
            .reading-value { color: white; font-weight: bold; font-size: 32px; }
            </style>
        """, unsafe_allow_html=True)

        h_disp = safe_float(last_data.get('난방', 0.0))
        c_disp = safe_float(last_data.get('냉방', 0.0))

        st.markdown(f"""
            <div class="reading-container">
                <div class="reading-box"><span class="reading-label">전기 전월:</span><span class="reading-value">{last_data.get('전기', '0')}</span></div>
                <div class="reading-box"><span class="reading-label">수도 전월:</span><span class="reading-value">{last_data.get('수도', '0')}</span></div>
                <div class="reading-box"><span class="reading-label">온수 전월:</span><span class="reading-value">{last_data.get('온수', '0')}</span></div>
                <div class="reading-box"><span class="reading-label">난방 전월:</span><span class="reading-value">{h_disp:.3f}</span></div>
                <div class="reading-box"><span class="reading-label">냉방 전월:</span><span class="reading-value">{c_disp:.3f}</span></div>
            </div>
        """, unsafe_allow_html=True)

# --- 7. 검침 수치 입력 폼 (세로 1열 배치) ---
with st.form("inspection_form", clear_on_submit=True):
    st.markdown("### ✍️ 이번 달 수치 입력")
    current_last_data = st.session_state.get('last_data', None)
    
    prev_e = current_last_data.get('전기', 0) if current_last_data is not None else 0
    prev_w = current_last_data.get('수도', 0) if current_last_data is not None else 0
    prev_h = current_last_data.get('온수', 0) if current_last_data is not None else 0
    prev_n = safe_float(current_last_data.get('난방', 0.0)) if current_last_data is not None else 0.0
    prev_c = safe_float(current_last_data.get('냉방', 0.0)) if current_last_data is not None else 0.0

    st.markdown(f"⚡ **전기** (지난번: {prev_e})")
    in_e = st.text_input("전기 입력", key="e_v", label_visibility="collapsed", placeholder="숫자만 입력")
    
    st.markdown(f"💧 **수도** (지난번: {prev_w})")
    in_w = st.text_input("수도 입력", key="w_v", label_visibility="collapsed", placeholder="숫자만 입력")
    
    st.markdown(f"♨️ **온수** (지난번: {prev_h})")
    in_h = st.text_input("온수 입력", key="h_v", label_visibility="collapsed", placeholder="숫자만 입력")
    
    st.markdown(f"🔥 **난방** (지난번: {prev_n:.3f})")
    in_n = st.text_input("난방 입력", key="n_v", label_visibility="collapsed", placeholder="숫자만 입력")
    
    st.markdown(f"❄️ **냉방** (지난번: {prev_c:.3f})")
    in_c = st.text_input("냉방 입력", key="c_v", label_visibility="collapsed", placeholder="숫자만 입력")

    st.divider()
    submit = st.form_submit_button(f"2. {room}호 저장하고 다음으로 🚀", use_container_width=True)

# --- 8. 데이터 전송 로직 ---
if submit:
    if not room:
        st.error("❗ 호수를 먼저 입력하고 데이터 찾기를 눌러주세요.")
    else:
        try:
            with st.spinner("저장 중입니다. 잠시만 기다려주세요..."):
                all_rows = sheet.get_all_values()
                all_rooms_ordered = [r[2] for r in all_rows if len(r) > 2][1:]
                
                res_e = safe_float(in_e) if in_e else safe_float(prev_e)
                res_w = safe_float(in_w) if in_w else safe_float(prev_w)
                res_h = safe_float(in_h) if in_h else safe_float(prev_h)
                res_n = safe_float(in_n) if in_n else safe_float(prev_n)
                res_c = safe_float(in_c) if in_c else safe_float(prev_c)

                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                row_data = [now, selected_building, room, round(res_e, 0), round(res_w, 0), round(res_n, 3), round(res_h, 0), round(res_c, 3)]

                if room in all_rooms_ordered:
                    row_idx = all_rooms_ordered.index(room) + 2
                    sheet.update(values=[row_data], range_name=f'A{row_idx}:H{row_idx}')
                    st.toast(f"✅ {room}호 저장 완료!")
                else:
                    sheet.append_row(row_data)
                    st.toast(f"✅ {room}호 신규 등록 완료!")

                next_room = ""
                if room in all_rooms_ordered:
                    idx = all_rooms_ordered.index(room)
                    if idx + 1 < len(all_rooms_ordered):
                        next_room = all_rooms_ordered[idx + 1]
                
                st.session_state['room_input'] = next_room
                if 'last_room' in st.session_state: del st.session_state['last_room']
                if 'last_data' in st.session_state: del st.session_state['last_data']
                
                st.rerun()
                    
        except Exception as e:
            st.error(f"❗ 저장 실패: {e}")

# 하단 타임스탬프 표시
st.markdown(f"<div style='text-align: right; color: #5d6d7e; font-size: 1em; margin-top: 50px;'>기록 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
