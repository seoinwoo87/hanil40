import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# ==========================================
# 1. 필수 설정 (부장님 시트 주소)
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 관리시스템", page_icon="🏫", layout="wide")

# 디자인: 중앙 정렬 및 가독성 강화 CSS
st.markdown("""
    <style>
    /* 전체 배경색 및 폰트 설정 */
    .stApp { background-color: #f0f2f5; }
    
    /* 중앙으로 모아주는 컨테이너 */
    .block-container { max-width: 900px; padding-top: 2rem !important; }
    
    /* 주간 안내 배너 */
    .week-banner {
        background: linear-gradient(135deg, #002147 0%, #003366 100%);
        color: white; padding: 30px; border-radius: 15px;
        text-align: center; margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .week-title { font-size: 1.2rem; opacity: 0.9; margin-bottom: 5px; }
    .week-date { font-size: 2.2rem; font-weight: 800; color: #deff9a; }
    
    /* 관리자 카드 스타일 */
    .admin-card {
        background: white; padding: 20px; border-radius: 12px;
        border-top: 5px solid #002147; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* 탭 스타일 조정 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; }
    .stTabs [data-baseweb="tab"] {
        background-color: #e9ecef; border-radius: 8px 8px 0 0; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #002147 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 데이터 세척 함수 (소수점 .0 완벽 제거)
# ==========================================
def clean_data(df):
    for col in ['학번', '반', '호실', '기숙사 호실']:
        if col in df.columns:
            # 소수점 제거 후 정수 문자열로 변환
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            # 빈 값 처리
            df[col] = df[col].replace('nan', '')
    return df

# ==========================================
# 3. 날짜 및 "대상주말" 계산
# ==========================================
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

# 월요일 08시 기준 주간 자동 전환
if now < deadline:
    target_sat = deadline + timedelta(days=5)
else:
    target_sat = deadline + timedelta(days=12)

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# --- [상단 메인 헤더] ---
st.markdown(f"""
    <div class="week-banner">
        <div class="week-title">🏫 한일고 40기 통합 신청 시스템</div>
        <div class="week-date">{target_weekend_str}</div>
        <div style="font-size: 0.9rem; margin-top: 10px; opacity: 0.8;">현재 위 주말에 대한 신청을 받고 있습니다.</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 학생 신청 제출", "👨‍🏫 관리자보고서"])

# ==========================================
# [TAB 1] 학생 신청 (중앙 집중형)
# ==========================================
with tab1:
    with st.container():
        with st.form("auth_form"):
            st.markdown("### 1. 본인 확인")
            input_sid = st.text_input("학번 4자리를 입력하세요", placeholder="예: 1101")
            auth_btn = st.form_submit_button("정보 불러오기")

        if input_sid:
            try:
                master_raw = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
                master_df = clean_data(master_raw)
                student = master_df[master_df['학번'] == input_sid.strip()]

                if not student.empty:
                    s_name = student.iloc[0]['이름']
                    s_class = student.iloc[0].get('반', "-")
                    s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', "-"))
                    
                    st.success(f"✅ **{s_class}반 {s_name}** 학생 확인 (호실: {s_room}호)")

                    with st.expander("📝 신청 내용 입력하기", expanded=True):
                        cat = st.radio("신청 종류", ["귀성", "토요외출", "일요외출"], horizontal=True)
                        reason = st.text_input("구체적 사유 및 목적지 (5자 이상)")
                        final_submit = st.button("🚀 최종 신청서 제출")

                    if final_submit:
                        if len(reason) < 5:
                            st.error("사유를 조금 더 구체적으로 적어주세요!")
                        else:
                            data_raw = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                            data_df = clean_data(data_raw)
                            
                            # 중복 체크
                            if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                                st.warning("⚠️ 이번 주말에 이미 신청한 내역이 있습니다.")
                            else:
                                new_row = pd.DataFrame([{
                                    "신청시간": datetime.now().strftime("%m-%d %H:%M"),
                                    "학번": input_sid.strip(), "이름": s_name, "반": s_class, "호실": s_room,
                                    "구분": cat, "사유": reason, "대상주말": target_weekend_str
                                }])
                                updated_all = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                                
                                conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_all)
                                this_week = updated_all[updated_all['대상주말'] == target_weekend_str]
                                conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=this_week)
                                
                                st.balloons()
                                st.success(f"🎉 신청이 완료되었습니다. ({target_weekend_str})")
                else:
                    st.error("❌ 학번을 찾을 수 없습니다. 다시 확인해 주세요.")
            except Exception as e:
                st.error(f"데이터 연동 중 오류: {e}")

# ==========================================
# [TAB 2] 관리자보고서 (가공 데이터 요약)
# ==========================================
with tab2:
    admin_pw = st.text_input("관리자 암호", type="password")
    if admin_pw == "hanil40":
        try:
            master_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0))
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            week_df = full_data[full_data['대상주말'] == target_weekend_str]

            # 상단 요약 지표
            m1, m2, m3 = st.columns(3)
            m1.metric("총 신청", f"{len(week_df)}명")
            m2.metric("미신청 학생", f"{len(master_df) - len(week_df)}명")
            m3.metric("금주 귀성", f"{len(week_df[week_df['구분']=='귀성'])}명")

            # 반별/호실별 요약
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div class='admin-card'><h4>🏫 학급별 현황</h4></div>", unsafe_allow_html=True)
                if not week_df.empty:
                    summary = week_df.groupby(['반', '구분']).size().unstack(fill_value=0)
                    st.dataframe(summary, use_container_width=True)
            with col2:
                st.markdown("<div class='admin-card'><h4>🏢 기숙사 호실별 현황</h4></div>", unsafe_allow_html=True)
                if not week_df.empty:
                    room_sum = week_df.groupby('호실').size().reset_index(name='인원')
                    st.dataframe(room_sum.sort_values('인원', ascending=False), use_container_width=True, hide_index=True)

            # 미신청자 명단 (부장님이 가장 필요하신 부분)
            st.markdown("<div class='admin-card'><h4>🔍 미신청 학생 추적 (마감 전 독촉용)</h4></div>", unsafe_allow_html=True)
            submitted_ids = week_df['학번'].unique()
            unsubmitted = master_df[~master_df['학번'].isin(submitted_ids)][['반', '학번', '이름', '호실']]
            if not unsubmitted.empty:
                st.dataframe(unsubmitted.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            else:
                st.success("✅ 모든 학생이 신청 완료했습니다!")

            # 상세 전체 명단
            st.markdown("### 📋 이번 주 상세 신청자 명단")
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 관리자 보고서(CSV) 다운로드", csv, f"40기_주간명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"보고서 생성 오류: {e}")
