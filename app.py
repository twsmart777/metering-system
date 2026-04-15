import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
import pandas as pd
import os
# --- [최종] 시각 경고 강화 버전 (깜빡이 5회) ---
@st.dialog("⚠️ 수치 오류")
def show_error_dialog(messages):
    # 1. 시각적 효과 (5번 깜빡임) & 소리 통합
    st.components.v1.html(
        """
        <div id="flash"></div>
        <script>
            function playSound() {
                try {
                    var AudioContext = window.AudioContext || window.webkitAudioContext;
                    var context = new AudioContext();
                    var oscillator = context.createOscillator();
                    var gainNode = context.createGain();
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(440, context.currentTime); 
                    gainNode.gain.setValueAtTime(0.1, context.currentTime);
                    oscillator.connect(gainNode);
                    gainNode.connect(context.destination);
                    oscillator.start();
                    oscillator.stop(context.currentTime + 0.2);
                } catch (e) { console.log(e); }
            }
            playSound();
        </script>
        <style>
            /* 0.3초 간격으로 5번 번쩍이는 애니메이션 */
            @keyframes blink { 
                0% { opacity: 0; } 
                50% { opacity: 0.7; } 
                100% { opacity: 0; } 
            }
            #flash { 
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; 
                background: red; z-index: 9999; pointer-events: none; 
                animation: blink 0.3s ease-in-out 5; /* 5회 반복 */
            }
        </style>
        """, height=0,
    )

    # 2. 직관적인 에러 표시
    st.error("### 📢 전월보다 낮음!")
    
    for msg in messages:
        st.markdown(f"## ❌ {msg}")
    
    st.divider()
    
    if st.button("🔴 확인 (수정하기)", use_container_width=True):
        st.rerun()

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

# --- 3. 보안 인증 로직 ---
if 'authenticated' not in st.session_state:
    # [임시 수정] 배포 전까지 무조건 True로 설정하여 인증 패스
    st.session_state['authenticated'] = True 

# 아래는 기존 인증 로직입니다. (현재는 실행되지 않도록 설정됨)
if not st.session_state['authenticated']:
    if url_building in BUILDING_LIST:
        target_pwd = SITE_PASSWORD
        header_msg = f"🔒 {url_building} 현장 인증"
    else:
        target_pwd = ADMIN_PASSWORD
        header_msg = f"🔒 {COMPANY_NAME} 관리자 인증"

    st.markdown(f"### {header_msg}")
    # key값은 유니크해야 하므로 유지합니다.
    input_pwd = st.text_input("비밀번호를 입력하세요", type="password", key="auth_pwd")

    if st.button("접속하기"):
        if input_pwd == target_pwd:
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("❌ 비밀번호가 일치하지 않습니다.")
    st.stop() # 인증되지 않았을 때만 여기서 실행 중단

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

# --- 5. 화면 디자인 로직 (수정됨) ---

# [수정] url_building(현장 파라미터)이 없을 때만 상단 프라임시티 로고 박스를 표시
if not url_building:
    st.markdown(f"""
        <div style='text-align: center; background-color: #1c2833; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
            <h2 style='color: #ecf0f1; margin: 0;'>{COMPANY_NAME}</h2>
            <p style='color: #95a5a6; margin: 5px 0 0 0; font-size: 0.9em;'>통합 검침 관리 시스템</p>
        </div>
        """, unsafe_allow_html=True)

# 현장 선택 및 표시부
if url_building in BUILDING_LIST:
    selected_building = url_building
    # 현장 링크로 접속 시 상단 로고 없이 바로 현장명 박스부터 시작
    st.markdown(f"""
        <div style='background-color: #d4edda; padding: 15px; border-radius: 8px; border: 2px solid #28a745; text-align: center; margin-bottom: 20px;'>
            <h3 style='color: #155724; margin: 0;'>🏢 {selected_building}</h3>
            <p style='margin: 5px 0 0 0; font-weight: bold; color: #155724; font-size: 0.9em;'>담당 현장이 맞는지 확인하세요</p>
        </div>
    """, unsafe_allow_html=True)
else:
    # 관리자 페이지(파라미터 없음)에서는 현장 선택창 표시
    selected_building = st.selectbox("🏗️ 검침 현장을 선택하세요", ["선택하세요"] + BUILDING_LIST)
    if selected_building == "선택하세요":
        st.info("전용 링크로 접속하거나 현장을 선택해 주세요.")
        st.stop()

# 시트 연결 및 유틸리티 함수 (기존과 동일)
try:
    sheet = spreadsheet.worksheet(selected_building)
except gspread.exceptions.WorksheetNotFound:
    sheet = spreadsheet.add_worksheet(title=selected_building, rows="1000", cols="10")
    sheet.append_row(["일시", "건물명", "호수", "전기", "수도", "온수", "난방", "냉방"])

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
st.markdown("""
    <style>
    /* 1. 전체 위젯에 대해 시스템 다크모드 강제 무시 */
    [data-testid="stTextInput"] {
        color-scheme: light !important;
    }

    /* 2. 입력창 전체 컨테이너 높이 */
    [data-testid="stTextInput"] > div {
        height: 75px !important;
    }

    /* 3. 입력창 내부 배경색과 글자색 강제 고정 */
    [data-testid="stTextInput"] > div > div {
        height: 75px !important;
        background-color: #f0f2f6 !important; /* 무조건 흰색 배경 */
          color: #000000 !important; /* 글자색 검정 */
    }

    /* 4. 실제 input 태그 내부 설정 (다크모드에서도 검정글자 유지) */
    [data-testid="stTextInput"] input {
        height: 75px !important;
        font-size: 22px !important;
        font-weight: bold !important;
        color: #000000 !important; /* 글자색 검정 */
        -webkit-text-fill-color: #000000 !important; /* iOS/사파리 강제 검정색 */
        background-color: transparent !important;
        padding: 0 15px !important;
    }

    /* 5. 플레이스홀더(안내문구) 색상도 흐린 회색으로 고정 */
    [data-testid="stTextInput"] input::placeholder {
        color: #888888 !important;
        -webkit-text-fill-color: #888888 !important;
    }

    /* 6. "⚡ 전기", "💧 수도" 같은 마크다운 텍스트 크기 */
    [data-testid="stMarkdownContainer"] p {
        font-size: 24px !important; /* 이 숫자를 조절해서 라벨 크기를 변경하세요 */
        font-weight: bold !important;
        margin-bottom: 5px !important; /* 입력창과의 간격을 좁힘 */
    }
    /* 전송 버튼(submit button)의 높이와 글자 크기 조절 */
    div[data-testid="stFormSubmitButton"] button {
        height: 90px !important;
        font-size: 24px !important;
        font-weight: bold !important;
        
        /* [중앙 정렬 보정] */
        display: flex !important;
        align-items: center !important;     /* 수직 중앙 정렬 */
        justify-content: center !important;  /* 수평 중앙 정렬 */
        line-height: 1 !important;           /* 기본 줄높이 초기화 */
        padding-top: 5px !important;         /* 만약 아래로 쏠려 보이면 0으로, 위로 쏠리면 숫자를 늘리세요 */
        
        /* [색상 설정] 시스템 다크모드 영향을 받지 않는 선명한 색 */
        background-color: #FFD700 !important; /* 밝은 골드/노란색 */
        color: #000000 !important;           /* 글자는 진한 검정 */
        border-radius: 12px !important;
        color-scheme: light !important;
    }
    
    /* 버튼을 눌렀을 때(Hover/Active) 살짝 어두워지는 효과 */
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #FFC400 !important;
        border-color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown(f"### 🔢 {selected_building} 호수 입력")
room_col, btn_col = st.columns([3, 1])

if 'room_input' not in st.session_state:
    st.session_state['room_input'] = ""

with room_col:
    room = st.text_input("호수", value=st.session_state['room_input'], placeholder="호수 입력", label_visibility="collapsed")
with btn_col:
    load_btn = st.button("조회 🔍", use_container_width=True)

if load_btn or (room and st.session_state.get('last_room') != room):
    st.session_state['last_room'] = room
    st.session_state['room_input'] = room
    last_data = get_last_reading(sheet, room)
    st.session_state['last_data'] = last_data
    
    if last_data is not None:
        st.success(f"📊 {room}호 전월 데이터 로딩완료")
        st.markdown("""
            <style>
            .reading-container { display: flex; justify-content: space-between; align-items: center; background-color: #262730; padding: 10px; border-radius: 5px; gap: 5px; }
            .reading-box { flex: 1; text-align: center; min-width: 0; }
            .reading-label { color: #95a5a6; font-size: clamp(10px, 3vw, 14px); margin-bottom: 2px; }
            .reading-value { color: white; font-weight: bold; font-size: clamp(12px, 4vw, 18px); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            </style>
        """, unsafe_allow_html=True)

        h_disp = safe_float(last_data.get('난방', 0.0))
        c_disp = safe_float(last_data.get('냉방', 0.0))

        st.markdown(f"""
            <div class="reading-container">
                <div class="reading-box"><div class="reading-label">전기</div><div class="reading-value">{last_data.get('전기', '-')}</div></div>
                <div class="reading-box"><div class="reading-label">수도</div><div class="reading-value">{last_data.get('수도', '-')}</div></div>
                <div class="reading-box"><div class="reading-label">온수</div><div class="reading-value">{last_data.get('온수', '-')}</div></div>
                <div class="reading-box"><div class="reading-label">난방</div><div class="reading-value">{h_disp:.3f}</div></div>
                <div class="reading-box"><div class="reading-label">냉방</div><div class="reading-value">{c_disp:.3f}</div></div>
            </div>
        """, unsafe_allow_html=True)

# --- 7. 검침 수치 입력 폼 ---
with st.form("inspection_form", clear_on_submit=True):
    current_site = str(selected_building).strip()
    limited_sites = ["더빌", "엘리트타워", "S타워"]
    is_limited = any(site == current_site for site in limited_sites)
    
    st.caption(f"📍 현재 현장: {current_site} / 필터링 적용: {'예' if is_limited else '아니오'}")
    st.markdown("### ✍️ {room}호 당월 수치 입력")
    
    # [중요] 데이터프레임 체크 및 전월 데이터 로딩을 최상단으로 이동
    current_last_data = st.session_state.get('last_data', None)
    has_data = current_last_data is not None and not (isinstance(current_last_data, pd.DataFrame) and current_last_data.empty)
    
    # 현장 종류와 상관없이 모든 전월 데이터를 여기서 미리 정의 (NameError 방지)
    prev_e = current_last_data.get('전기', 0) if has_data else 0
    prev_w = current_last_data.get('수도', 0) if has_data else 0
    prev_h = current_last_data.get('온수', 0) if has_data else 0
    prev_n = safe_float(current_last_data.get('난방', 0.0)) if has_data else 0.0
    prev_c = safe_float(current_last_data.get('냉방', 0.0)) if has_data else 0.0

    # 1. 공통 항목: 전기, 수도 (모든 현장 표시)
    st.markdown(f"⚡ **전기** (<span style='font-size: 0.7em; color: #95a5a6;'>전월</span>_ {prev_e} kw)", unsafe_allow_html=True)
    in_e = st.text_input("전기", key="e_v", label_visibility="collapsed", placeholder="")
    
    st.markdown(f"💧 **수도** (<span style='font-size: 0.7em; color: #95a5a6;'>전월</span>_ {prev_w} $m^3$)", unsafe_allow_html=True)
    in_w = st.text_input("수도", key="w_v", label_visibility="collapsed", placeholder="")

    # 2. 조건부 항목: 온수, 난방, 냉방
    if not is_limited:
        # 일반 현장: 입력창 표시
        st.markdown(f"🔥 **온수** (<span style='font-size: 0.7em; color: #95a5a6;'>전월</span>_ {prev_h} $m^3$)", unsafe_allow_html=True)
        in_h = st.text_input("온수", key="h_v", label_visibility="collapsed", placeholder="")
        
        st.markdown(f"♨️ **난방** (<span style='font-size: 0.7em; color: #95a5a6;'>전월</span>_ {prev_n:.3f} MWh)", unsafe_allow_html=True)
        in_n = st.text_input("난방", key="n_v", label_visibility="collapsed", placeholder="")
        
        st.markdown(f"❄️ **냉방** (<span style='font-size: 0.7em; color: #95a5a6;'>전월</span>_ {prev_c:.3f} MWh)", unsafe_allow_html=True)
        in_c = st.text_input("냉방", key="c_v", label_visibility="collapsed", placeholder="")
    else:
        # S타워 등 제한 현장: 입력창은 숨기고 위에서 정의한 prev 값을 계승
        in_h = str(prev_h)
        in_n = str(prev_n)
        in_c = str(prev_c)

    st.divider()
    # 폼 버튼이 조건문 밖에 있는지 확인
    submit = st.form_submit_button("🚀 전송. 호수이동", use_container_width=True)

# --- 8. 데이터 전송 로직 ---
if submit:
    if not room:
        st.error("❗ 호수를 입력해 주세요.")
    else:
        # 1. 입력값 수치화 (입력하지 않았으면 전월값으로 대체)
        res_e = safe_float(in_e) if in_e else safe_float(prev_e)
        res_w = safe_float(in_w) if in_w else safe_float(prev_w)
        res_h = safe_float(in_h) if in_h else safe_float(prev_h)
        res_n = safe_float(in_n) if in_n else safe_float(prev_n)
        res_c = safe_float(in_c) if in_c else safe_float(prev_c)

        # 2. [검증] 전월 대비 수치 검사
        error_msg = []
        if res_e < prev_e: error_msg.append(f"전기({int(res_e)} < {int(prev_e)})")
        if res_w < prev_w: error_msg.append(f"수도({int(res_w)} < {int(prev_w)})")
        if res_h < prev_h: error_msg.append(f"온수({int(res_h)} < {int(prev_h)})")
        if res_n < prev_n: error_msg.append(f"난방({res_n:.3f} < {prev_n:.3f})")
        if res_c < prev_c: error_msg.append(f"냉방({res_c:.3f} < {prev_c:.3f})")

        if error_msg:
            # 팝업창 띄우기 (알림음 포함)
            show_error_dialog(error_msg)
            st.stop()

        # 3. 데이터 저장 프로세스 시작
        try:
            with st.spinner("데이터 처리 중..."):
                all_rows = sheet.get_all_values()
                all_rooms_ordered = [r[2] for r in all_rows if len(r) > 2][1:] # 헤더 제외 순서 유지

                kst = timezone(timedelta(hours=9))
                now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                row = [now, selected_building, room, round(res_e, 0), round(res_w, 0), round(res_h, 0), round(res_n, 3), round(res_c, 3)]

                if room in all_rooms_ordered:
                    row_idx = all_rooms_ordered.index(room) + 2
                    sheet.update(range_name=f'A{row_idx}:H{row_idx}', values=[row])
                    st.toast(f"✅ {room}호 변경수정 완료!")
                else:
                    sheet.append_row(row)
                    st.toast(f"✅ {room}호 저장 완료!")

                # 다음 호수 찾기: 시트의 물리적 순서 그대로 따라감 (정렬 금지)
                next_room = ""
                if room in all_rooms_ordered:
                    idx = all_rooms_ordered.index(room)
                    if idx + 1 < len(all_rooms_ordered):
                        next_room = all_rooms_ordered[idx + 1]
                
                st.session_state['room_input'] = next_room
                if 'last_room' in st.session_state: del st.session_state['last_room']
                if 'last_data' in st.session_state: del st.session_state['last_data']
                
                st.rerun() # 완료 후 새로고침
                    
        except Exception as e:
            st.error(f"❗ 오류 발생: {e}")

st.markdown(f"<div style='text-align: right; color: #5d6d7e; font-size: 0.8em; margin-top: 30px;'>[2026-04-12 05:45]</div>", unsafe_allow_html=True)
