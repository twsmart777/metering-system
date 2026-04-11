import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import os

# --- 1. 설정 (배포할 건물명 리스트) ---
COMPANY_NAME = "프라임시티"
JSON_FILE = 'service_account.json' 
BUILDING_LIST = ["더빌", "엘리트타워", "장안프라임광교", "장안프라임광교2", "S타워", "킹덤부띠크"]
# 구글 시트 접근 권한 범위 (이 줄이 반드시 필요합니다)
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- 2. 구글 시트 연결 (로컬/배포 통합 로직) ---
try:
    if os.path.exists(JSON_FILE):
        # 로컬: 폴더에 파일이 있을 때
        creds = Credentials.from_service_account_file(JSON_FILE, scopes=scope)
    else:
        # 배포: 파일이 없을 때 (Secrets 사용)
        info = dict(st.secrets["gcp_service_account"])
        # 핵심: 텍스트 안의 \n을 실제 줄바꿈으로 변환
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=scope)
    
    client = gspread.authorize(creds)
    spreadsheet = client.open("검침데이터_관리")
    
except Exception as e:
    st.error(f"⚠️ 연결 오류 발생: {e}")
    st.stop() # 연결 실패 시 아래 로직 실행 안 함

# --- 3. 주소창 파라미터 읽기 (전용 링크 핵심) ---
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

# 건물 결정 및 고정 로직
if url_building in BUILDING_LIST:
    selected_building = url_building
    st.markdown(f"""
        <div style='background-color: #d4edda; padding: 15px; border-radius: 8px; border: 2px solid #28a745; text-align: center;'>
            <h3 style='color: #155724; margin: 0;'>🏢 {selected_building}</h3>
            <p style='margin: 5px 0 0 0; font-weight: bold; color: #155724;'>본인 담당 현장이 맞는지 확인하세요</p>
        </div>
    """, unsafe_allow_html=True)
else:
    # 링크 없이 들어왔을 경우에만 선택창 노출 (관리자용)
    selected_building = st.selectbox("🏗️ 검침 현장을 선택하세요", ["선택하세요"] + BUILDING_LIST)
    if selected_building == "선택하세요":
        st.info("전용 링크로 접속하거나 현장을 선택해 주세요.")
        st.stop()

# 해당 건물의 시트(탭) 연결
try:
    sheet = spreadsheet.worksheet(selected_building)
except gspread.exceptions.WorksheetNotFound:
    sheet = spreadsheet.add_worksheet(title=selected_building, rows="1000", cols="20")
    sheet.append_row(["일시", "건물명", "호수", "전기", "수도", "난방", "온수", "냉방", "사진상태"])

# --- 전월 데이터 불러오기 함수 ---
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
with room_col:
    room = st.text_input("호수", placeholder="호수 입력", label_visibility="collapsed")
with btn_col:
    load_btn = st.button("조회 🔍", use_container_width=True)

last_data = None
if load_btn or (room and st.session_state.get('last_room') != room):
    st.session_state['last_room'] = room
    last_data = get_last_reading(sheet, room)
    if last_data is not None:
        st.success(f"📊 {room}호 전월 데이터를 불러왔습니다.")
        
# 가로로 강제 정렬하고 글자 크기를 화면 폭에 맞추는 스타일
        st.markdown("""
            <style>
            .reading-container {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background-color: #262730;
                padding: 10px;
                border-radius: 5px;
                gap: 5px;
            }
            .reading-box {
                flex: 1;
                text-align: center;
                min-width: 0; /* 폭 좁아질 때 글자 잘림 방지 */
            }
            .reading-label {
                color: #95a5a6;
                font-size: clamp(10px, 3vw, 14px); /* 화면 폭에 따라 글자 크기 조절 */
                margin-bottom: 2px;
            }
            .reading-value {
                color: white;
                font-weight: bold;
                font-size: clamp(12px, 4vw, 18px); /* 화면 폭에 따라 글자 크기 조절 */
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            </style>
        """, unsafe_allow_html=True)

        # 실제 수치 표시 부분
        st.markdown(f"""
            <div class="reading-container">
                <div class="reading-box"><div class="reading-label">전기</div><div class="reading-value">{last_data['전기']}</div></div>
                <div class="reading-box"><div class="reading-label">수도</div><div class="reading-value">{last_data['수도']}</div></div>
                <div class="reading-box"><div class="reading-label">온수</div><div class="reading-value">{last_data['온수']}</div></div>
                <div class="reading-box"><div class="reading-label">난방</div><div class="reading-value">{last_data['난방']:.3f}</div></div>
                <div class="reading-box"><div class="reading-label">냉방</div><div class="reading-value">{last_data['냉방']:.3f}</div></div>
            </div>
        """, unsafe_allow_html=True)
        
# --- 6. 검침 수치 입력 폼 ---
with st.form("inspection_form", clear_on_submit=True):
    st.markdown("### ✍️ 당월 수치 입력")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"⚡ **전기** (전월: {last_data['전기'] if last_data is not None else '-'})")
        elec = st.text_input("전기", key="elec_val", label_visibility="collapsed", placeholder="공란 시 0")
        st.markdown(f"💧 **수도** (전월: {last_data['수도'] if last_data is not None else '-'})")
        water = st.text_input("수도", key="water_val", label_visibility="collapsed", placeholder="공란 시 0")
        st.markdown(f"♨️ **온수** (전월: {last_data['온수'] if last_data is not None else '-'})")
        hotwater = st.text_input("온수", key="hotwater_val", label_visibility="collapsed", placeholder="공란 시 0")
        
    with col2:
        st.markdown(f"🔥 **난방** (전월: {f'{last_data['난방']:.3f}' if last_data is not None else '-'})")
        heat = st.text_input("난방", key="heat_val", label_visibility="collapsed", placeholder="0.000")
        st.markdown(f"❄️ **냉방** (전월: {f'{last_data['냉방']:.3f}' if last_data is not None else '-'})")
        cool = st.text_input("냉방", key="cool_val", label_visibility="collapsed", placeholder="0.000")
        
    st.divider()
    photo = st.camera_input("📸 사진 촬영 (선택)")
    submit = st.form_submit_button(f"🚀 {selected_building} 데이터 전송", use_container_width=True)

    if submit:
        if not room:
            st.error("❗ 호수를 입력해 주세요.")
        else:
            try:
                def to_float(v): return float(v.strip()) if v.strip() else 0.0
                with st.spinner("전송 중..."):
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    photo_status = "확인됨" if photo is not None else "미첨부"
                    row = [now, selected_building, room, round(to_float(elec), 2), round(to_float(water), 2), 
                           round(to_float(heat), 3), round(to_float(hotwater), 2), round(to_float(cool), 3), photo_status]
                    sheet.append_row(row)
                    st.success(f"✅ {selected_building} {room}호 전송 완료!")
                    st.balloons()
            except ValueError:
                st.error("❗ 숫자와 소수점만 입력해 주세요.")
