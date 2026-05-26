import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 필수 설정 (부장님 시트 주소)
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 관리시스템", page_icon="🏫", layout="wide")

# 디자인: 중앙 정렬 및 가독성 강화 CSS
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .block-container { max-width: 900px; padding-top: 2rem !important; }
    
    /* 주간 안내 배너 */
    .week-banner {
        background: linear-gradient(135deg, #001a33 0%, #003366 100%);
        color: white; padding: 30px; border-radius: 15px;
        text-align: center; margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .week-title { font-size: 1.1rem; opacity: 0.9; margin-bottom: 5px; }
    .week-date { font-size: 2.2rem; font-weight: 800; color: #deff9a; }
    
    /* 카드 스타일 */
    .admin-card {
        background: white; padding: 20px; border-radius: 12px;
        border-top: 5px solid #001a33; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; }
    .stTabs [aria-selected="true"] { background-color: #001a33 !important; color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 데이터 세척 함수 (소수점 .0 제거)
# ==========================================
def clean_data(df):
    for col in ['학번', '반', '호실', '기숙사 호실']:
        if col in df.columns:
            # 소수점 제거 후 정수 문자열로 변환
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df[col] = df[col].replace('nan', '')
    return df

# ==========================================
# 3. 날짜 계산 (대상 주말 고정)
# ==========================================
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

if now < deadline:
    target_sat = deadline + timedelta(days=5)
else:
    target_sat = deadline + timedelta(days=12)

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# --- [상단 메인 배너] ---
st.markdown(f"""
    <div class="week-banner">
        <div class="week-title">🏫 한일고 40기 통합 신청 시스템</div>
        <div class="week-date">{target_weekend_str}</div>
        <div style="font-size: 0.9rem; margin-top: 10px; opacity: 0.8;">현재 위 주말에 대한 신청을 접수하고 있습니다.</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 학생 신청 제출", "👨‍🏫 교사용"])

# ==========================================
# [TAB 1] 학생 신청 (중앙 정렬)
# ==========================================
with tab1:
    with st.form("auth_form"):
        st.markdown("### 1. 학생 본인 확인")
        input_sid = st.text_input("학번 4자리를 입력하세요", placeholder="예: 1101")
        auth_btn = st.form_submit_button("내 정보 불러오기")

    if input_sid:
        try:
            # 마스터 로드 및 세척
            master_raw = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
            master_df = clean_data(master_raw)
            student = master_df[master_df['학번'] == input_sid.strip()]

            if not student.empty:
                s_name = student.iloc[0]['이름']
                s_class = student.iloc[0].get('반', "-")
                s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', "-"))
                
                st.success(f"✅ **{s_class}반 {s_name}** 학생 확인 (호실: {s_room}호)")

                with st.expander("📝 상세 신청 내용 작성", expanded=True):
                    # --- [복구된 시간 필드] ---
                    cat = st.radio("신청 구분", ["귀성", "토요외출", "일요외출"], horizontal=True)
                    time_opt = ["토요일 오후", "일요일 오전", "일요일 오후", "기타(사유란 기재)"]
                    stime = st.selectbox("귀가/외출 예정 시간", time_opt)
                    
                    reason = st.text_input("사유 및 목적지 (5자 이상 구체적으로)")
                    final_submit = st.button("🚀 최종 신청서 제출")

                if final_submit:
                    if len(reason) < 5:
                        st.error("사유를 조금 더 상세히 입력해 주세요.")
                    else:
                        data_raw = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                        data_df = clean_data(data_raw)
                        
                        # 중복 신청 체크
                        if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                            st.warning("⚠️ 이미 이번 신청 주간에 제출된 내역이 있습니다.")
                        else:
                            # 데이터 구성 (귀가/외출 일시 포함)
                            new_row = pd.DataFrame([{
                                "신청시간": datetime.now().strftime("%m-%d %H:%M"),
                                "학번": input_sid.strip(), 
                                "이름": s_name, 
                                "반": s_class, 
                                "호실": s_room,
                                "구분": cat, 
                                "귀가/외출 일시": stime,  # 이 부분이 복구되었습니다!
                                "사유": reason, 
                                "대상주말": target_weekend_str
                            }])
                            
                            updated_all = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                            
                            # 3개 시트 동시 기록
                            conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_all)
                            this_week = updated_all[updated_all['대상주말'] == target_weekend_str]
                            conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=this_week)
                            
                            st.balloons()
                            st.success(f"🎉 신청이 정상 완료되었습니다! (대상: {target_weekend_str})")
            else:
                st.error("❌ 명단에 없는 학번입니다. 학번을 다시 확인해 주세요.")
        except Exception as e:
            st.error(f"오류 발생: {e}")

# ==========================================
# [TAB 2] 교사용 (깔끔한 보고서 중심)
# ==========================================
with tab2:
    admin_pw = st.text_input("교사용 암호 입력", type="password")
    if admin_pw == "hanil40":
        try:
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            week_df = full_data[full_data['대상주말'] == target_weekend_str]

            # 상단 요약
            st.markdown(f"### 📊 {target_weekend_str} 신청 요약")
            m1, m2, m3 = st.columns(3)
            m1.metric("총 신청 인원", f"{len(week_df)}명")
            m2.metric("귀성 인원", f"{len(week_df[week_df['구분']=='귀성'])}명")
            m3.metric("외출 인원", f"{len(week_df[week_df['구분'].str.contains('외출')])}명")

            # 반별/호실별 분석
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div class='admin-card'><h4>🏫 학급별 현황</h4></div>", unsafe_allow_html=True)
                if not week_df.empty:
                    summary = week_df.groupby(['반', '구분']).size().unstack(fill_value=0)
                    st.table(summary)
            with col2:
                st.markdown("<div class='admin-card'><h4>🏢 호실별 인원</h4></div>", unsafe_allow_html=True)
                if not week_df.empty:
                    room_sum = week_df.groupby('호실').size().reset_index(name='인원')
                    st.dataframe(room_sum.sort_values('인원', ascending=False), use_container_width=True, hide_index=True)

            # 상세 명단
            st.markdown("### 📋 이번 주 상세 신청 명단")
            # 학급 및 학번 순으로 정렬하여 보기 편하게 제공
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            # 다운로드 버튼
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 관리자용 보고서 다운로드 (CSV)", csv, f"40기_주간명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터 로드 오류: {e}")

