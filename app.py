import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# --- 1. 설정 ---
COMPANY_NAME = "프라임시티"
BUILDING_LIST = ["더빌", "엘리트타워", "장안프라임광교", "장안프라임광교2", "S타워", "킹덤부띠크"]

# --- 2. 구글 시트 연결 (수정된 부분) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    # 스트림릿 설정창(Secrets)에 입력한 정보를 읽어옵니다.
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("검침데이터_관리")
except Exception as e:
    st.error(f"⚠️ 연결 오류 발생: {e}")
    st.info("스트림릿 Settings -> Secrets 창에 구글 인증 정보를 넣으셨는지 확인해주세요.")
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
    st.markdown(f"<div style='background-color: #d4edda; padding: 15px; border-radius: 8px; border: 2px solid #28a745; text-align: center;'><h3 style='color: #155724; margin: 0;'>🏢 {selected_building}</h3></div>", unsafe_allow_html=True)
else:
    selected_building = st.selectbox("🏗️ 검침 현장을 선택하세요", ["선택하세요"] + BUILDING_LIST)
    if selected_building == "선택하세요":
        st.stop()

try:
    sheet = spreadsheet.worksheet(selected_building)
except gspread.exceptions.WorksheetNotFound:
    sheet = spreadsheet.add_worksheet(title=selected_building, rows="1000", cols="20")
    sheet.append_row(["일시", "건물명", "호수", "전기", "수도", "난방", "온수", "냉방", "사진상태"])

# 이후 검침 로직 (기존과 동일)
def get_last_reading(target_sheet, room_number):
    try:
        data = target_sheet.get_all_records()
        if not data: return None
        df = pd.DataFrame(data)
        filtered_df = df[df['호수'].astype(str) == str(room_number)]
        return filtered_df.iloc[-1] if not filtered_df.empty else None
    except: return None

st.divider()
room = st.text_input("🔢 호수 입력", placeholder="예: 101")
last_data = None
if room:
    last_data = get_last_reading(sheet, room)
    if last_data is not None:
        st.success(f"📊 {room}호 전월 데이터를 불러왔습니다.")
        m_col = st.columns(5)
        m_col[0].metric("전기", last_data['전기'])
        m_col[1].metric("수도", last_data['수도'])
        m_col[2].metric("온수", last_data['온수'])
        m_col[3].metric("난방", f"{last_data['난방']:.3f}")
        m_col[4].metric("냉방", f"{last_data['냉방']:.3f}")

with st.form("inspection_form", clear_on_submit=True):
    st.markdown("### ✍️ 당월 수치 입력")
    col1, col2 = st.columns(2)
    with col1:
        elec = st.text_input("⚡ 전기", placeholder="0")
        water = st.text_input("💧 수도", placeholder="0")
        hotwater = st.text_input("♨️ 온수", placeholder="0")
    with col2:
        heat = st.text_input("🔥 난방", placeholder="0.000")
        cool = st.text_input("❄️ 냉방", placeholder="0.000")
    
    photo = st.camera_input("📸 사진 촬영")
    submit = st.form_submit_button(f"🚀 {selected_building} 데이터 전송")

    if submit:
        if not room:
            st.error("❗ 호수를 입력해 주세요.")
        else:
            try:
                def to_float(v): return float(v.strip()) if v.strip() else 0.0
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                row = [now, selected_building, room, to_float(elec), to_float(water), to_float(heat), to_float(hotwater), to_float(cool), "확인됨" if photo else "미첨부"]
                sheet.append_row(row)
                st.success(f"✅ 전송 완료!")
                st.balloons()
            except Exception as e:
                st.error(f"오류 발생: {e}")
