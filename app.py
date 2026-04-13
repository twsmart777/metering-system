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

# --- 2. 화면 설정 및 파라미터 읽기 (인증 판별용) ---
st.set_page_config(page_title=f"{COMPANY_NAME} 통합검침", layout="centered")

# 주소창 파라미터 읽기
url_params = st.query_params
url_building = url_params.get("b", None)

# --- 3. 보안 인증 로직 (최우선 실행) ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    # 현장 링크인지 메인 주소인지 판별하여 비번 설정
    if url_building in BUILDING_LIST:
        target_pwd = SITE_PASSWORD
        header_msg = f"🔒 {url_building} 현장 인증"
    else:
        target_pwd = ADMIN_PASSWORD
        header_msg = f"🔒 {COMPANY_NAME} 관리자 인증"

    st.markdown(f"### {header_msg}")
    input_pwd = st.text_input("비밀번호를 입력하세요", type="password", key="auth_pwd")
    
    if st.button("접속하기"):
        if input_pwd == target_pwd:
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("❌ 비밀번호가 일치하지 않습니다.")
    st.stop()

# --- 4. 구글 시트 연결 (인증 통과 후) ---
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

# --- 5. 화면 디자인 로직 (로고 박스 출력 로직 완전 수정) ---

# 1. 현재 접속이 유효한 현장 링크인지 체크 (True/False)
is_site_access = url_building in BUILDING_LIST

# 2. 현장 접속이 아닐 때(관리자일 때)만 상단 프라임시티 박스 출력
if is_site_access == False:
    st.markdown(f"""
        <div style='text-align: center; background-color: #1c2833; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
            <h1 style='color: #ecf0f1; margin: 0; font-size: 45px;'>{COMPANY_NAME}</h1>
            <p style='color: #95a5a6; margin: 10px 0 0 0; font-size: 24px;'>통합 검침 관리 시스템</p>
        </div>
        """, unsafe_allow_html=True)

# 3. 현장 표시 및 선택 영역
if is_site_access:
    selected_building = url_building
    # 현장 링크 접속 시: 로고 없이 현장명만 크게
    st.markdown(f"""
        <div style='background-color: #d4edda; padding: 20px; border-radius: 10px; border: 3px solid #28a745; text-align: center; margin-bottom: 25px;'>
            <h2 style='color: #155724; margin: 0; font-size: 40px;'>🏢 {selected_building}</h2>
        </div>
    """, unsafe_allow_html=True)
else:
    # 관리자 접속 시: 현장 선택 셀렉트박스 표시
    selected_building = st.selectbox("🏗️ 현장을 선택하세요", ["선택하세요"] + BUILDING_LIST)
    if selected_building == "선택하세요":
        st.info("현장을 선택해 주세요.")
        st.stop()

# --- 시트 연결 및 유틸리티 함수 (여기서부터는 기존과 동일) ---
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

# --- 6 & 7. 검침 통합 입력 폼 (호수 자동 전환 및 엔터 제어) ---

# UI 스타일 설정
st.markdown("""
    <style>
    input {
        height: 120px !important;
        font-size: 60px !important;
        font-weight: bold !important;
        color: #1ed760 !important;
    }
    input::placeholder { font-size: 30px !important; color: #95a5a6 !important; }
    div[data-baseweb="input"] { height: 120px !important; border-radius: 15px !important; }
    .stMarkdown p { font-size: 35px !important; font-weight: bold !important; margin-top: 20px !important; }
    .stButton button { height: 100px !important; font-size: 40px !important; font-weight: bold !important; margin-top: 30px !important; }
    </style>
""", unsafe_allow_html=True)

# 엔터키 제어 JavaScript (폼 내부 엔터 -> 다음 칸 / 마지막 -> 전송)
st.components.v1.html("""
<script>
    const doc = window.parent.document;
    const inputs = Array.from(doc.querySelectorAll('input'));
    inputs.forEach((input, index) => {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const next = inputs[index + 1];
                if (next && next.type !== 'submit') {
                    next.focus();
                } else {
                    const submitBtn = doc.querySelector('button[kind="primaryFormSubmit"]');
                    if (submitBtn) submitBtn.click();
                }
            }
        });
    });
</script>
""", height=0)

# 세션 상태 초기화
if 'room_input' not in st.session_state:
    st.session_state['room_input'] = ""

with st.form("inspection_form", clear_on_submit=False): # 다음 호수 유지를 위해 False로 설정
    st.markdown(f"### 🔢 {selected_building} 정보 입력")
    
    # [중요] 호수 입력창을 폼 안으로 넣어 엔터 흐름에 포함시킴
    room = st.text_input("호수", value=st.session_state['room_input'], key="room_val", placeholder="호수 입력")
    
    # 데이터 조회 로직 (호수가 바뀔 때 자동으로 전월 데이터 매칭)
    last_data = get_last_reading(sheet, room) if room else None
    
    if last_data is not None:
        p_e = last_data.get('전기', 0)
        p_w = last_data.get('수도', 0)
        p_h = last_data.get('온수', 0)
        p_n = safe_float(last_data.get('난방', 0.0))
        p_c = safe_float(last_data.get('냉방', 0.0))
        st.info(f"📊 {room}호 전월 데이터를 불러왔습니다.")
    else:
        p_e = p_w = p_h = 0
        p_n = p_c = 0.0

    st.divider()
    st.markdown("### ✍️ 당월 수치 입력")
    
    st.markdown(f"⚡ **전기** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_e})</span>", unsafe_allow_html=True)
    in_e = st.text_input("전기", key="e_v", label_visibility="collapsed", placeholder=f"직전 {p_e}")
    
    st.markdown(f"💧 **수도** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_w})</span>", unsafe_allow_html=True)
    in_w = st.text_input("수도", key="w_v", label_visibility="collapsed", placeholder=f"직전 {p_w}")
    
    st.markdown(f"♨️ **온수** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_h})</span>", unsafe_allow_html=True)
    in_h = st.text_input("온수", key="h_v", label_visibility="collapsed", placeholder=f"직전 {p_h}")
    
    st.markdown(f"🔥 **난방** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_n:.3f})</span>", unsafe_allow_html=True)
    in_n = st.text_input("난방", key="n_v", label_visibility="collapsed", placeholder=f"직전 {p_n:.3f}")
    
    st.markdown(f"❄️ **냉방** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_c:.3f})</span>", unsafe_allow_html=True)
    in_c = st.text_input("냉방", key="c_v", label_visibility="collapsed", placeholder=f"직전 {p_c:.3f}")

    st.divider()
    submit = st.form_submit_button(f"🚀 {selected_building} 데이터 저장 후 이동", use_container_width=True)

# --- 8. 데이터 전송 로직 ---
if submit:
    if not room:
        st.error("❗ 호수를 입력해 주세요.")
    else:
        try:
            with st.spinner("저장 중..."):
                all_rows = sheet.get_all_values()
                all_rooms_ordered = [r[2] for r in all_rows if len(r) > 2][1:]
                
                # 입력값이 없으면 전월값 사용
                res_e = safe_float(in_e) if in_e else safe_float(p_e)
                res_w = safe_float(in_w) if in_w else safe_float(p_w)
                res_h = safe_float(in_h) if in_h else safe_float(p_h)
                res_n = safe_float(in_n) if in_n else safe_float(p_n)
                res_c = safe_float(in_c) if in_c else safe_float(p_c)

                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                row = [now, selected_building, room, round(res_e, 0), round(res_w, 0), round(res_n, 3), round(res_h, 0), round(res_c, 3)]

                if room in all_rooms_ordered:
                    row_idx = all_rooms_ordered.index(room) + 2
                    sheet.update(range_name=f'A{row_idx}:H{row_idx}', values=[row])
                else:
                    sheet.append_row(row)

                # [핵심] 다음 호수 결정 및 세션 업데이트
                next_room = ""
                if room in all_rooms_ordered:
                    idx = all_rooms_ordered.index(room)
                    if idx + 1 < len(all_rooms_ordered):
                        next_room = all_rooms_ordered[idx + 1]
                
                st.session_state['room_input'] = next_room  # 다음 호수를 세션에 저장
                st.toast(f"✅ {room}호 저장 완료! 다음 호수({next_room})로 이동합니다.")
                st.rerun()  # 화면을 새로고침하여 다음 호수를 value에 반영
                
        except Exception as e:
            st.error(f"❗ 오류 발생: {e}")

st.markdown(f"<div style='text-align: right; color: #5d6d7e; font-size: 0.8em; margin-top: 30px;'>[2026-04-13 17:15]</div>", unsafe_allow_html=True)# --- 6 & 7. 검침 통합 입력 폼 (호수 자동 전환 및 엔터 제어) ---

# UI 스타일 설정
st.markdown("""
    <style>
    input {
        height: 120px !important;
        font-size: 60px !important;
        font-weight: bold !important;
        color: #1ed760 !important;
    }
    input::placeholder { font-size: 30px !important; color: #95a5a6 !important; }
    div[data-baseweb="input"] { height: 120px !important; border-radius: 15px !important; }
    .stMarkdown p { font-size: 35px !important; font-weight: bold !important; margin-top: 20px !important; }
    .stButton button { height: 100px !important; font-size: 40px !important; font-weight: bold !important; margin-top: 30px !important; }
    </style>
""", unsafe_allow_html=True)

# 엔터키 제어 JavaScript (폼 내부 엔터 -> 다음 칸 / 마지막 -> 전송)
st.components.v1.html("""
<script>
    const doc = window.parent.document;
    const inputs = Array.from(doc.querySelectorAll('input'));
    inputs.forEach((input, index) => {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const next = inputs[index + 1];
                if (next && next.type !== 'submit') {
                    next.focus();
                } else {
                    const submitBtn = doc.querySelector('button[kind="primaryFormSubmit"]');
                    if (submitBtn) submitBtn.click();
                }
            }
        });
    });
</script>
""", height=0)

# 세션 상태 초기화
if 'room_input' not in st.session_state:
    st.session_state['room_input'] = ""

with st.form("inspection_form", clear_on_submit=False): # 다음 호수 유지를 위해 False로 설정
    st.markdown(f"### 🔢 {selected_building} 정보 입력")
    
    # [중요] 호수 입력창을 폼 안으로 넣어 엔터 흐름에 포함시킴
    room = st.text_input("호수", value=st.session_state['room_input'], key="room_val", placeholder="호수 입력")
    
    # 데이터 조회 로직 (호수가 바뀔 때 자동으로 전월 데이터 매칭)
    last_data = get_last_reading(sheet, room) if room else None
    
    if last_data is not None:
        p_e = last_data.get('전기', 0)
        p_w = last_data.get('수도', 0)
        p_h = last_data.get('온수', 0)
        p_n = safe_float(last_data.get('난방', 0.0))
        p_c = safe_float(last_data.get('냉방', 0.0))
        st.info(f"📊 {room}호 전월 데이터를 불러왔습니다.")
    else:
        p_e = p_w = p_h = 0
        p_n = p_c = 0.0

    st.divider()
    st.markdown("### ✍️ 당월 수치 입력")
    
    st.markdown(f"⚡ **전기** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_e})</span>", unsafe_allow_html=True)
    in_e = st.text_input("전기", key="e_v", label_visibility="collapsed", placeholder=f"직전 {p_e}")
    
    st.markdown(f"💧 **수도** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_w})</span>", unsafe_allow_html=True)
    in_w = st.text_input("수도", key="w_v", label_visibility="collapsed", placeholder=f"직전 {p_w}")
    
    st.markdown(f"♨️ **온수** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_h})</span>", unsafe_allow_html=True)
    in_h = st.text_input("온수", key="h_v", label_visibility="collapsed", placeholder=f"직전 {p_h}")
    
    st.markdown(f"🔥 **난방** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_n:.3f})</span>", unsafe_allow_html=True)
    in_n = st.text_input("난방", key="n_v", label_visibility="collapsed", placeholder=f"직전 {p_n:.3f}")
    
    st.markdown(f"❄️ **냉방** <span style='font-size:24px; color:#95a5a6;'>(전월: {p_c:.3f})</span>", unsafe_allow_html=True)
    in_c = st.text_input("냉방", key="c_v", label_visibility="collapsed", placeholder=f"직전 {p_c:.3f}")

    st.divider()
    submit = st.form_submit_button(f"🚀 {selected_building} 데이터 저장 후 이동", use_container_width=True)

# --- 8. 데이터 전송 로직 ---
if submit:
    if not room:
        st.error("❗ 호수를 입력해 주세요.")
    else:
        try:
            with st.spinner("저장 중..."):
                all_rows = sheet.get_all_values()
                all_rooms_ordered = [r[2] for r in all_rows if len(r) > 2][1:]
                
                # 입력값이 없으면 전월값 사용
                res_e = safe_float(in_e) if in_e else safe_float(p_e)
                res_w = safe_float(in_w) if in_w else safe_float(p_w)
                res_h = safe_float(in_h) if in_h else safe_float(p_h)
                res_n = safe_float(in_n) if in_n else safe_float(p_n)
                res_c = safe_float(in_c) if in_c else safe_float(p_c)

                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                row = [now, selected_building, room, round(res_e, 0), round(res_w, 0), round(res_n, 3), round(res_h, 0), round(res_c, 3)]

                if room in all_rooms_ordered:
                    row_idx = all_rooms_ordered.index(room) + 2
                    sheet.update(range_name=f'A{row_idx}:H{row_idx}', values=[row])
                else:
                    sheet.append_row(row)

                # [핵심] 다음 호수 결정 및 세션 업데이트
                next_room = ""
                if room in all_rooms_ordered:
                    idx = all_rooms_ordered.index(room)
                    if idx + 1 < len(all_rooms_ordered):
                        next_room = all_rooms_ordered[idx + 1]
                
                st.session_state['room_input'] = next_room  # 다음 호수를 세션에 저장
                st.toast(f"✅ {room}호 저장 완료! 다음 호수({next_room})로 이동합니다.")
                st.rerun()  # 화면을 새로고침하여 다음 호수를 value에 반영
                
        except Exception as e:
            st.error(f"❗ 오류 발생: {e}")

st.markdown(f"<div style='text-align: right; color: #5d6d7e; font-size: 0.8em; margin-top: 30px;'>[2026-04-13 17:15]</div>", unsafe_allow_html=True)
