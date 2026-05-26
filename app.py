import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 필수 설정 (부장님 시트 주소)
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 관리시스템 v3.5", page_icon="🏫", layout="wide")

# 디자인: 중앙 정렬 및 McKinsey 스타일 CSS
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    
    /* 중앙 집중형 레이아웃 */
    .centered-container {
        max-width: 800px; margin: 0 auto; padding-top: 1rem;
    }
    
    /* 주간 배너 디자인 */
    .main-banner {
        background: linear-gradient(135deg, #002147 0%, #003366 100%);
        color: white; padding: 35px; border-radius: 15px;
        text-align: center; margin-bottom: 30px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .banner-sub { font-size: 1rem; opacity: 0.8; margin-bottom: 8px; letter-spacing: 1px; }
    .banner-main { font-size: 2.3rem; font-weight: 800; color: #deff9a; }
    
    /* 깔끔한 카드 스타일 */
    .info-card {
        background: white; padding: 25px; border-radius: 12px;
        border-top: 6px solid #002147; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    
    /* 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    .stTabs [aria-selected="true"] { background-color: #002147 !important; color: white !important; font-weight: bold; border-radius: 8px 8px 0 0; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 세척 함수
def clean_df(df):
    for col in ['학번', '반', '호실', '기숙사 호실']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df[col] = df[col].replace('nan', '')
    return df

# 날짜 및 대상주말 계산
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

if now < deadline:
    target_sat = deadline + timedelta(days=5)
else:
    target_sat = deadline + timedelta(days=12)

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# --- [상단 헤더 배너] ---
st.markdown(f"""
    <div class="centered-container">
        <div class="main-banner">
            <div class="banner-sub">🏫 한일고 40기 통합 신청 시스템</div>
            <div class="banner-main">{target_weekend_str}</div>
            <div style="font-size: 0.9rem; margin-top: 12px; opacity: 0.7;">현재 위 주말에 대한 신청을 받고 있습니다.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 탭 구성
tab1, tab2 = st.tabs(["📝 학생 신청 제출", "👨‍🏫 교사용"])

# ==========================================
# [TAB 1] 학생 신청
# ==========================================
with tab1:
    st.markdown('<div class="centered-container">', unsafe_allow_html=True)
    
    with st.form("student_form"):
        st.markdown("### 1. 학생 정보 확인")
        input_sid = st.text_input("학번 4자리를 입력하세요", placeholder="예: 1101")
        check_btn = st.form_submit_button("내 정보 불러오기")

    if input_sid:
        try:
            master_raw = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
            master_df = clean_df(master_raw)
            student = master_df[master_df['학번'] == input_sid.strip()]

            if not student.empty:
                s_name = student.iloc[0]['이름']
                s_class = student.iloc[0].get('반', "-")
                s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', "-"))
                
                st.success(f"✅ **{s_class}반 {s_name}** 학생 확인 완료 (호실: {s_room}호)")

                with st.expander("📝 신청 내용 작성하기", expanded=True):
                    # 1. 구분 단순화 (귀성, 외출)
                    cat = st.radio("신청 종류", ["귀성", "외출"], horizontal=True)
                    
                    # 2. 시간 선택 로직
                    time_opt = ["토요일 오후", "일요일 오전", "일요일 오후", "기타"]
                    stime = st.selectbox("귀가/외출 예정 시간", time_opt)
                    
                    # '기타' 선택 시 상세 시간 입력창 등장
                    detailed_time = ""
                    if stime == "기타":
                        detailed_time = st.text_input("상세 시간 입력 (예: 토요일 14:00)")
                    
                    # 사유 입력
                    base_reason = st.text_input("사유 및 목적지 (5자 이상)")
                    final_submit = st.button("🚀 최종 신청서 제출")

                if final_submit:
                    if len(base_reason) < 5:
                        st.error("사유를 조금 더 구체적으로 적어주세요!")
                    elif stime == "기타" and not detailed_time:
                        st.error("기타 선택 시 상세 시간을 입력해야 합니다.")
                    else:
                        # 데이터 저장 준비
                        data_raw = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                        data_df = clean_df(data_raw)
                        
                        # 중복 신청 체크
                        if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                            st.warning("⚠️ 이번 주말에 이미 제출된 신청 내역이 있습니다.")
                        else:
                            # 사유와 상세 시간 병합 (부장님 요청사항)
                            final_reason = base_reason
                            if stime == "기타":
                                final_reason = f"[{detailed_time}] {base_reason}"
                            
                            new_row = pd.DataFrame([{
                                "신청시간": datetime.now().strftime("%m-%d %H:%M"),
                                "학번": input_sid.strip(), "이름": s_name, "반": s_class, "호실": s_room,
                                "구분": cat, "귀가/외출 일시": stime, "사유": final_reason, "대상주말": target_weekend_str
                            }])
                            updated_all = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                            
                            conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_all)
                            this_week = updated_all[updated_all['대상주mal'] == target_weekend_str] # '대상주말' 오타 주의
                            this_week = updated_all[updated_all['대상주말'] == target_weekend_str] # 교정
                            conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=this_week)
                            
                            st.success(f"🎉 신청이 정상 완료되었습니다. ({target_weekend_str})")
                            st.balloons()
            else:
                st.error("❌ 학번을 찾을 수 없습니다. 다시 확인해 주세요.")
        except Exception as e:
            st.error(f"오류: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# [TAB 2] 교사용 (중앙 집중형)
# ==========================================
with tab2:
    st.markdown('<div class="centered-container">', unsafe_allow_html=True)
    admin_pw = st.text_input("교사용 암호", type="password")
    if admin_pw == "hanil40":
        try:
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            week_df = full_data[full_data['대상주말'] == target_weekend_str]

            # 상단 요약 통계 카드
            st.markdown(f"### 📊 {target_weekend_str} 요약")
            c1, c2, c3 = st.columns(3)
            c1.metric("총 신청", f"{len(week_df)}명")
            c2.metric("귀성", f"{len(week_df[week_df['구분']=='귀성'])}명")
            c3.metric("외출", f"{len(week_df[week_df['구분']=='외출'])}명")

            # 학급/호실별 상세
            st.markdown("<div class='info-card'><h4>🏫 학급별 신청 현황</h4></div>", unsafe_allow_html=True)
            if not week_df.empty:
                st.table(week_df.groupby(['반', '구분']).size().unstack(fill_value=0))
            
            st.markdown("<div class='info-card'><h4>🏢 호실별 인원 요약</h4></div>", unsafe_allow_html=True)
            if not week_df.empty:
                room_sum = week_df.groupby('호실').size().reset_index(name='명')
                st.dataframe(room_sum.sort_values('명', ascending=False), use_container_width=True, hide_index=True)

            # 상세 전체 명단
            st.markdown("### 📋 금주 상세 신청 명단")
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            # CSV 다운로드
            csv_data = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 보고서 데이터(CSV) 다운로드", csv_data, f"40기_명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터 로드 오류: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

