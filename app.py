import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
import pandas as pd
import os
kst = timezone(timedelta(hours=9))
now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

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
st.set_page_config(page_title=f"{COMPANY_NAME} 통합검침", layout="wide")

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
# =========================================================
# 📝 [추가 및 수정 로직] 현장별 시트 탭 대응
if client:
    try:
        # 전체 스프레드시트 열기
        spr = client.open("검침데이터_관리")
        
        # 1. 현장 정보 기준 시트 (고정)
        info_sheet = spr.worksheet("현장정보")
        
    except Exception as e:
        st.error(f"⚠️ 시트 열기 실패: {e}")
        st.stop()
else:
    st.stop()
# =========================================================
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

# =========================================================
# 5-1📝 [교체 로직] spr 변수 적용 및 현장별 시트/호수 로드 (최종본)
try:
    #  현장별 검침기록 시트 연결 (4번에서 정의한 spr 사용)
    sheet = spr.worksheet(selected_building)
except gspread.exceptions.WorksheetNotFound:
    # 18개 컬럼 관리를 위해 신규 생성
    sheet = spr.add_worksheet(title=selected_building, rows="1000", cols="20")
    header = ["일시", "현장명", "호수", 
              "전기-전월", "전기-당월", "전기사용량", 
              "수도-전월", "수도-당월", "수도사용량", 
              "온수-전월", "온수-당월", "온수사용량", 
              "난방-전월", "난방-당월", "난방사용량", 
              "냉방-전월", "냉방-당월", "냉방사용량"]
    sheet.append_row(header)

# 5-2. [현장정보] 시트에서 호수 명단 불러오기
try:
    info_data = info_sheet.get_all_records()
    room_list = [str(row['호수']).strip() for row in info_data if str(row['현장명']).strip() == selected_building]
    all_rooms = room_list
    st.session_state['all_rooms'] = all_rooms
except Exception as e:
    st.error(f"⚠️ '현장정보' 시트를 읽어올 수 없습니다: {e}")
    all_rooms = []

# 📝 [5-3 최종] 7일 필터링 + 사용자님의 안전한 컬럼 매칭 로직 통합
def get_last_reading(target_sheet, room_number):
    try:
        data = target_sheet.get_all_records()
        if not data: return None
        
        df = pd.DataFrame(data)
        df['호수'] = df['호수'].astype(str).str.strip()
        search_room = str(room_number).strip()
        
        kst = timezone(timedelta(hours=9))
        now_dt = datetime.now(kst)
        
        room_df = df[df['호수'] == search_room].copy()
        if room_df.empty: return None

        # 1. [필터링] 7일 이내 기록은 전월 지침에서 제외 (재입력/수정 시 방어)
        def is_valid_prev_data(date_str):
            try:
                record_date = datetime.strptime(str(date_str), '%Y-%m-%d %H:%M:%S').replace(tzinfo=kst)
                return (now_dt - record_date).days > 7
            except:
                return False

        valid_prev_df = room_df[room_df['일시'].apply(is_valid_prev_data)]
        
        # 7일 이전 데이터가 있으면 그것을 사용, 없으면 전체 중 첫 번째(가장 오래된 것) 사용
        last_row = valid_prev_df.iloc[-1] if not valid_prev_df.empty else room_df.iloc[0]

        # 2. [사용자님 원래 로직 그대로] 이중 체크 매핑
        result = {
            '전기': last_row.get('전기-당월') if '전기-당월' in last_row else last_row.get('전기', 0),
            '수도': last_row.get('수도-당월') if '수도-당월' in last_row else last_row.get('수도', 0),
            '온수': last_row.get('온수-당월') if '온수-당월' in last_row else last_row.get('온수', 0),
            '난방': last_row.get('난방-당월') if '난방-당월' in last_row else last_row.get('난방', 0.0),
            '냉방': last_row.get('냉방-당월') if '냉방-당월' in last_row else last_row.get('냉방', 0.0)
        }
        return result
    except:
        return None
# =========================================================

def safe_float(val):
    try:
        if val is None or val == "" or str(val).isspace(): return 0.0
        return float(val)
    except: return 0.0

st.divider()

# --- 6. 호수 입력 및 데이터 조회 (기존 UI 복구 및 넘김 로직 통합) ---
st.markdown(f"### 🔢 {selected_building} 호수 입력")

# [보존] 다음 호수 전이 로직
if 'next_room' in st.session_state:
    st.session_state['room_input'] = st.session_state.next_room
    st.session_state['last_room'] = st.session_state.next_room
    del st.session_state['next_room']

if 'room_input' not in st.session_state:
    st.session_state['room_input'] = ""

# [보존] 원래의 입력창 및 조회 버튼 배치
room = st.text_input("호수", value=st.session_state['room_input'], placeholder="호수 입력", label_visibility="collapsed")
load_btn = st.button("🔍 전월 데이터 조회", use_container_width=True)

if load_btn or (room and st.session_state.get('last_room') != room):
    st.session_state['last_room'] = room
    st.session_state['room_input'] = room
    last_data = get_last_reading(sheet, room)
    st.session_state['last_data'] = last_data
    
    if last_data is not None:
        st.markdown(f"<div class='loading-bar'>✅ {room}호 전월 데이터 로딩완료</div>", unsafe_allow_html=True)
        # [보존] 사용자님의 원래 검정 박스 스타일
        st.markdown("""
            <style>
            .reading-container { display: flex; justify-content: space-around; align-items: center; background-color: #262730; padding: 15px; border-radius: 5px; gap: 10px; margin-bottom: 15px; }
            .reading-box { text-align: center; min-width: 60px; }
            .reading-label { color: #95a5a6; font-size: 14px; margin-bottom: 2px; }
            .reading-value { color: white; font-weight: bold; font-size: 20px; }
            </style>
        """, unsafe_allow_html=True)

        boxes_html = ""
        for item in ['전기', '수도', '온수', '난방', '냉방']:
            val = last_data.get(item, 0)
            if item == '전기' or (val and float(str(val).replace(',', '')) > 0):
                d_val = f"{float(str(val).replace(',', '')):.3f}" if item in ['난방', '냉방'] else val
                boxes_html += f'<div class="reading-box"><div class="reading-label">{item}</div><div class="reading-value">{d_val}</div></div>'
        st.markdown(f'<div class="reading-container">{boxes_html}</div>', unsafe_allow_html=True)

# --- 7. 당월 수치 입력 섹션 (전송 버튼 삭제 및 디자인 유지) ---
submit = False         
if room:
    st.markdown(f"### ✍️ <span style='font-size:30px; color:blue;'>{room}</span>호 당월 수치 입력", unsafe_allow_html=True)
    
    current_last_data = st.session_state.get('last_data', None)
    is_limited = any(site == str(selected_building).strip() for site in ["더빌", "엘리트타워", "S타워"])

    prev_e = current_last_data.get('전기', 0) if current_last_data else 0
    prev_w = current_last_data.get('수도', 0) if current_last_data else 0
    prev_h = current_last_data.get('온수', 0) if current_last_data else 0
    prev_n = safe_float(current_last_data.get('난방', 0.0)) if current_last_data else 0.0
    prev_c = safe_float(current_last_data.get('냉방', 0.0)) if current_last_data else 0.0

    show_items = ['전기', '수도']
    if not is_limited: show_items.extend(['온수', '난방', '냉방'])
    item_map = {'전기': prev_e, '수도': prev_w, '온수': prev_h, '난방': prev_n, '냉방': prev_c}

    for item in show_items:
        icon = {"전기": "⚡", "수도": "💧", "온수": "🔥", "난방": "♨️", "냉방": "❄️"}[item]
        unit = {"전기": "kw", "수도": "m³", "온수": "m³", "난방": "MWh", "냉방": "MWh"}[item]
        p_val = item_map[item]
        p_str = f"{p_val:.3f}" if item in ['난방', '냉방'] else f"{p_val}"

        st.markdown(f"{icon} **{item}** <span style='font-size: 16px; color: #666;'>(전월_ {p_str} {unit})</span>", unsafe_allow_html=True)
        
        # [보존] 입력창 고유 key 유지 (리셋용)
        if item == '전기': in_e = st.text_input(item, key="e_v", label_visibility="collapsed")
        elif item == '수도': in_w = st.text_input(item, key="w_v", label_visibility="collapsed")
        elif item == '온수': in_h = st.text_input(item, key="h_v", label_visibility="collapsed")
        elif item == '난방': in_n = st.text_input(item, key="n_v", label_visibility="collapsed")
        elif item == '냉방': in_c = st.text_input(item, key="c_v", label_visibility="collapsed")

    if is_limited: in_h, in_n, in_c = str(prev_h), str(prev_n), str(prev_c)
    
    st.divider()
    if st.button("🚀 데이터 전송 후 다음 호수로", use_container_width=True, key="main_move_btn"):
        submit = True

# --- 8. 데이터 전송 로직 (사용자 기존 저장 로직 100% 보존) ---
if submit:
    if not room:
        st.error("❗ 호수를 입력해 주세요.")
    else:
        res_e = safe_float(in_e) if in_e else safe_float(prev_e)
        res_w = safe_float(in_w) if in_w else safe_float(prev_w)
        res_h = safe_float(in_h) if in_h else safe_float(prev_h)
        res_n = safe_float(in_n) if in_n else safe_float(prev_n)
        res_c = safe_float(in_c) if in_c else safe_float(prev_c)

        error_msg = []
        if res_e < prev_e: error_msg.append(f"전기({int(res_e)} < {int(prev_e)})")
        if res_w < prev_w: error_msg.append(f"수도({int(res_w)} < {int(prev_w)})")
        if res_h < prev_h: error_msg.append(f"온수({int(res_h)} < {int(prev_h)})")
        if res_n < prev_n: error_msg.append(f"난방({res_n:.3f} < {prev_n:.3f})")
        if res_c < prev_c: error_msg.append(f"냉방({res_c:.3f} < {prev_c:.3f})")

        if error_msg:
            show_error_dialog(error_msg)
            st.stop()

        try:
            with st.spinner("데이터 기록 중..."):
                kst = timezone(timedelta(hours=9))
                now_dt = datetime.now(kst)
                now_str = now_dt.strftime('%Y-%m-%d %H:%M:%S')

                new_row = [
                    now_str, selected_building, room,
                    float(round(prev_e, 0)), float(round(res_e, 0)), float(round(res_e - prev_e, 0)),
                    float(round(prev_w, 0)), float(round(res_w, 0)), float(round(res_w - prev_w, 0)),
                    float(round(prev_h, 0)), float(round(res_h, 0)), float(round(res_h - prev_h, 0)),
                    float(round(prev_n, 3)), float(round(res_n, 3)), float(round(res_n - prev_n, 3)),
                    float(round(prev_c, 3)), float(round(res_c, 3)), float(round(res_c - prev_c, 3))
                ]

                # [보존] 사용자 저장 로직
                data = sheet.get_all_records()
                df = pd.DataFrame(data)
                target_row_idx = -1 
                if not df.empty:
                    df['호수'] = df['호수'].astype(str).str.strip()
                    room_df = df[df['호수'] == str(room).strip()]
                    if not room_df.empty:
                        last_date_str = str(room_df.iloc[-1]['일시'])
                        try:
                            last_date = datetime.strptime(last_date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=kst)
                            if (now_dt - last_date).days <= 7:
                                target_row_idx = int(room_df.index[-1]) + 2
                        except: pass

                if target_row_idx != -1:
                    sheet.update(f"A{target_row_idx}:R{target_row_idx}", [new_row])
                else:
                    sheet.append_row(new_row)

                # [기능 추가] 다음 호수 설정 및 리셋
                rooms_list = st.session_state.get('all_rooms', [])
                if room in rooms_list:
                    idx = rooms_list.index(room)
                    st.session_state.next_room = rooms_list[idx + 1] if idx + 1 < len(rooms_list) else rooms_list[0]

                for k in ["e_v", "w_v", "h_v", "n_v", "c_v", "last_data"]:
                    if k in st.session_state: st.session_state[k] = ""
                
                st.rerun()
        except Exception as e:
            st.error(f"❗ 오류 발생: {e}")

st.markdown(f"<div style='text-align: right; color: #5d6d7e; font-size: 0.8em; margin-top: 30px;'>[{now}]</div>", unsafe_allow_html=True)
