import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import os

# --- 1. 설정 ---
COMPANY_NAME = "프라임시티"
JSON_FILE = 'service_account.json' 
BUILDING_LIST = ["더빌", "엘리트타워", "장안프라임광교", "장안프라임광교2", "S타워", "킹덤부띠크"]

# [중요] 403 오류 방지를 위해 드라이브 권한을 scope에 포함합니다.
scope = [
    "https://www.googleapis.com/auth/spreadsheets", 
    "https://www.googleapis.com/auth/drive"
]

# --- 2. 구글 시트 연결 ---
try:
    if os.path.exists(JSON_FILE):
        creds = Credentials.from_service_account_file(JSON_FILE, scopes=scope)
    else:
        info = dict(st.secrets["gcp_service_account"])
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=scope)
    
    client = gspread.authorize(creds)
    spreadsheet = client.open("검침데이터_관리")
    
except Exception as e:
    st.error(f"⚠️ 연결 오류 발생: {e}")
    st.stop()

# --- 3. 주소창 파라미터 읽기 ---
query_params = st.query_params
url_building = query_params.get("b", None)

# --- 4. 화면 디자인 ---
st.set_page_config(page_title=f"{COMPANY_NAME} 통합검침", layout="centered")

st.markdown(f"""
    <div style='text-align: center; background-color: #1c2833; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h2 style='color: #ecf0f1; margin: 0;'>{COMPANY_NAME}</h2>
        <p style='color: #95a5a6; margin: 5px 0 0 0; font-size: 0.9em;'>현장별 전용 검침 시스템</p>
    </div>
    """, unsafe_allow_html=True)

if url_building in BUILDING_LIST:
    selected_building = url_building
    st.markdown(f"""
        <div style='background-color: #d4edda; padding: 15px; border-radius: 8px; border: 2px solid #28a745; text-align: center;'>
            <h3 style='color: #155724; margin: 0;'>🏢 {selected_building}</h3>
            <p style='margin: 5px 0 0 0; font-weight: bold; color: #155724;'>본인 담당 현장이 맞는지 확인하세요</p>
        </div>
    """, unsafe_allow_html=True)
else:
    selected_building = st.selectbox("🏗️ 검침 현장을 선택하세요", ["선택하세요"] + BUILDING_LIST)
    if selected_building == "선택하세요":
        st.info("전용 링크로 접속하거나 현장을 선택해 주세요.")
        st.stop()

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

st.divider()

# --- 5. 호수 입력 및 데이터 조회 ---
st.markdown(f"### 🔢 {selected_building} 호수 입력")
room_col, btn_col = st.columns([3, 1])

# 세션 상태에 저장된 호수가 있으면 기본값으로 사용
if 'room_input' not in st.session_state:
    st.session_state['room_input'] = ""

with room_col:
    room = st.text_input("호수", value=st.session_state['room_input'], placeholder="호수 입력", label_visibility="collapsed")
with btn_col:
    load_btn = st.button("조회 🔍", use_container_width=True)

last_data = None
# 호수 입력값이 변경되었거나 조회 버튼 클릭 시 데이터 로드
if load_btn or (room and st.session_state.get('last_room') != room):
    st.session_state['last_room'] = room
    st.session_state['room_input'] = room
    last_data = get_last_reading(sheet, room)
    st.session_state['last_data'] = last_data
    
    if last_data is not None:
        st.success(f"📊 {room}호 전월 데이터를 불러왔습니다.")
        st.markdown("""
            <style>
            .reading-container { display: flex; justify-content: space-between; align-items: center; background-color: #262730; padding: 10px; border-radius: 5px; gap: 5px; }
            .reading-box { flex: 1; text-align: center; min-width: 0; }
            .reading-label { color: #95a5a6; font-size: clamp(10px, 3vw, 14px); margin-bottom: 2px; }
            .reading-value { color: white; font-weight: bold; font-size: clamp(12px, 4vw, 18px); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div class="reading-container">
                <div class="reading-box"><div class="reading-label">전기</div><div class="reading-value">{last_data.get('전기', '-')}</div></div>
                <div class="reading-box"><div class="reading-label">수도</div><div class="reading-value">{last_data.get('수도', '-')}</div></div>
                <div class="reading-box"><div class="reading-label">온수</div><div class="reading-value">{last_data.get('온수', '-')}</div></div>
                <div class="reading-box"><div class="reading-label">난방</div><div class="reading-value">{last_data.get('난방', 0.0):.3f}</div></div>
                <div class="reading-box"><div class="reading-label">냉방</div><div class="reading-value">{last_data.get('냉방', 0.0):.3f}</div></div>
            </div>
        """, unsafe_allow_html=True)

# --- 6. 검침 수치 입력 폼 ---
with st.form("inspection_form", clear_on_submit=True):
    st.markdown("### ✍️ 당월 수치 입력")
    
    last_data = st.session_state.get('last_data', None)
    
    def get_prev(key):
        if last_data is not None and key in last_data:
            try: return last_data[key]
            except: return 0
        return 0

    prev_e = get_prev('전기')
    prev_w = get_prev('수도')
    prev_h = get_prev('온수')
    prev_n = get_prev('난방')
    prev_c = get_prev('냉방')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"⚡ **전기** (전월: {prev_e})")
        in_e = st.text_input("전기", key="e_v", label_visibility="collapsed", placeholder=f"기존: {prev_e}")
        st.markdown(f"💧 **수도** (전월: {prev_w})")
        in_w = st.text_input("수도", key="w_v", label_visibility="collapsed", placeholder=f"기존: {prev_w}")
        st.markdown(f"♨️ **온수** (전월: {prev_h})")
        in_h = st.text_input("온수", key="h_v", label_visibility="collapsed", placeholder=f"기존: {prev_h}")
    with col2:
        st.markdown(f"🔥 **난방** (전월: {float(prev_n):.3f})")
        in_n = st.text_input("난방", key="n_v", label_visibility="collapsed", placeholder=f"기존: {float(prev_n):.3f}")
        st.markdown(f"❄️ **냉방** (전월: {float(prev_c):.3f})")
        in_c = st.text_input("냉방", key="c_v", label_visibility="collapsed", placeholder=f"기존: {float(prev_c):.3f}")

    st.divider()
    submit = st.form_submit_button(f"🚀 {selected_building} 데이터 전송", use_container_width=True)

def get_prev_final(key):
    if last_data is not None:
        val = last_data.get(key, None)
        if val in [None, "", " "]: return 0
        return val
    return 0

def safe_value(input_val, prev_val):
    if input_val is None or input_val.strip() == "":
        return float(prev_val) if prev_val is not None else 0
    return float(input_val)

if submit:
    if not room:
        st.error("❗ 호수를 입력해 주세요.")
    else:
        try:
            with st.spinner("데이터 처리 중..."):
                last_data = get_last_reading(sheet, room)

                p_e = get_prev_final('전기')
                p_w = get_prev_final('수도')
                p_h = get_prev_final('온수')
                p_n = get_prev_final('난방')
                p_c = get_prev_final('냉방')

                res_e = safe_value(in_e, p_e)
                res_w = safe_value(in_w, p_w)
                res_h = safe_value(in_h, p_h)
                res_n = safe_value(in_n, p_n)
                res_c = safe_value(in_c, p_c)

                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                row = [
                    now, selected_building, room,
                    round(res_e, 0),
                    round(res_w, 0),
                    round(res_n, 3),
                    round(res_h, 0),
                    round(res_c, 3)
                ]

                all_rooms = sheet.col_values(3)
                if room in all_rooms:
                    row_idx = all_rooms.index(room) + 1
                    sheet.update(range_name=f'A{row_idx}:H{row_idx}', values=[row])
                    st.toast(f"✅ {room}호 수정 완료!")
                else:
                    sheet.append_row(row)
                    st.toast(f"✅ {room}호 저장 완료!")

                # --- 다음 호수 자동 세팅 로직 ---
                try:
                    next_room = str(int(room) + 1)
                    st.session_state['room_input'] = next_room
                    # 다음 호수 조회를 위해 세션 초기화
                    if 'last_room' in st.session_state:
                        del st.session_state['last_room']
                    if 'last_data' in st.session_state:
                        del st.session_state['last_data']
                    
                    st.success(f"데이터가 저장되었습니다. 다음 호수({next_room}호)로 이동합니다.")
                    st.rerun()
                except ValueError:
                    # 호수가 숫자가 아닌 경우 (예: "관리실") 다음 호수 계산 건너뜀
                    st.balloons()
                    
        except Exception as e:
            st.error(f"❗ 오류: {e}")

st.markdown(f"<div style='text-align: right; color: #5d6d7e; font-size: 0.8em; margin-top: 30px;'>[2026-04-12 04:14]</div>", unsafe_allow_html=True)
