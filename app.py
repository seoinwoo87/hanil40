import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# [중요!] 부장님의 구글 시트 주소를 아래 큰따옴표 안에 꼭 넣어주세요.
# 예: SHEET_URL = "https://docs.google.com/spreadsheets/d/1abc.../edit#gid=0"
SHEET_URL = "https://docs.google.com/spreadsheets/d/부장님의_시트_ID/edit#gid=0"

# 1. 페이지 설정 및 커스텀 디자인
st.set_page_config(page_title="한일고 40기 귀성/외출 신청", page_icon="🏫", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .main-title {
        text-align: center; color: #002147; font-size: 2.5em; font-weight: 800;
        margin-bottom: 10px; padding: 20px;
    }
    .status-box { 
        background: linear-gradient(135deg, #002147 0%, #003366 100%); 
        color: white; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 30px;
    }
    .stButton>button { 
        width: 100%; border-radius: 10px; height: 3.8em; 
        background-color: #002147; color: white; font-weight: bold; font-size: 1.1em;
        border: none; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #c5a059; color: white; transform: translateY(-2px); }
    .warning-text {
        color: #d32f2f; background-color: #ffebee; padding: 15px;
        border-radius: 8px; border-left: 5px solid #d32f2f; margin-bottom: 20px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 날짜 및 마감 계산 (월요일 08:00 기준)
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

if now < deadline:
    target_sat = deadline + timedelta(days=5) 
else:
    target_sat = deadline + timedelta(days=12)

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# 3. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# --- [화면 상단 타이틀] ---
st.markdown('<h1 class="main-title">🏫 한일고 40기 귀성/외출 신청서</h1>', unsafe_allow_html=True)

st.markdown(f"""
    <div class="status-box">
        <p style="margin:0; opacity:0.8;">현재 신청 중인 주말</p>
        <p style="font-size:1.8em; margin:10px 0;"><b>{target_weekend_str}</b></p>
        <p style="color:#c5a059; font-weight:bold; margin:0;">● 정직한 신청이 한일고의 명예입니다.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="warning-text">
        ⚠️ [도용 금지] 타인의 정보를 도용하여 신청할 경우 관련 규정에 따라 엄중히 처치합니다. 
        반드시 본인 학번과 성명으로 신청하십시오.
    </div>
    """, unsafe_allow_html=True)

# --- [입력 폼 영역] ---
st.subheader("👤 학생 정보 입력")
col1, col2 = st.columns(2)
with col1:
    student_id = st.text_input("학번 (4자리)", placeholder="예: 1101")
with col2:
    name = st.text_input("성명", placeholder="실명 입력")

st.markdown("---")
st.subheader("📍 신청 내역")
category = st.radio("신청 구분", ["귀성", "토요외출", "일요외출"], horizontal=True)

col3, col4 = st.columns(2)
with col3:
    time_options = ["토요일 오후", "일요일 오전", "일요일 오후", "기타"]
    selected_time = st.selectbox("예정 시간", time_options)
    
    final_time = selected_time
    if selected_time == "기타":
        final_time = st.text_input("상세 시간 직접 입력", placeholder="예: 토요일 19시")
with col4:
    reason = st.text_input("사유 및 목적지", placeholder="예: 공주터미널, 병원 등")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("##### ✍️ 최종 확인")
confirm_check = st.checkbox("입력한 정보가 본인의 것임을 확인했으며, 제출 후 수정을 위해 선생님께 직접 연락드림에 동의합니다.")

# --- [제출 로직] ---
if st.button("🚀 신청서 제출하기"):
    if not (student_id.isdigit() and len(student_id) == 4):
        st.error("학번 4자리를 숫자로 정확히 입력해 주세요.")
    elif not name:
        st.error("성명을 입력해 주세요.")
    elif selected_time == "기타" and not final_time:
        st.error("기타 시간을 구체적으로 작성해 주세요.")
    elif not confirm_check:
        st.warning("동의 체크박스에 체크해 주셔야 제출이 가능합니다.")
    else:
        try:
            # [수정 포인트] worksheet 이름을 'data'로 설정 (한일고 인코딩 에러 해결)
            df = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl="0")
            df = df.dropna(how="all")

            new_row = pd.DataFrame([{
                "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "학번": student_id,
                "이름": name,
                "구분": category,
                "귀가/외출 일시": final_time,
                "사유": reason if reason else "없음",
                "대상주말": target_weekend_str
            }])
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            # [수정 포인트] 저장할 때도 'data' 워크시트로 저장
            conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_df)
            
            st.success(f"🎉 접수 완료! {name} 학생, 주말 계획이 안전하게 저장되었습니다.")
            st.balloons()
        except Exception as e:
            st.error(f"저장 중 오류 발생! (시트 이름이 'data'인지 확인하세요): {e}")

# --- [관리자 모드] ---
st.markdown("<br><hr>", unsafe_allow_html=True)
with st.expander("👨‍🏫 학년부 선생님 전용 관리 모드"):
    admin_pw = st.text_input("관리자 비밀번호", type="password")
    if admin_pw == "hanil40":
        try:
            # [수정 포인트] 여기서도 'data' 워크시트 참조
            admin_df = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl="0")
            st.write(f"### 📊 전체 신청 현황 (총 {len(admin_df)}건)")
            st.dataframe(admin_df, use_container_width=True)
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
