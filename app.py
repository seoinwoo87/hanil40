import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# [필수] 부장님 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

# 1. 페이지 설정
st.set_page_config(page_title="한일고 40기 프로 보고서", page_icon="🏫", layout="wide")

# CSS: 관리자 모드 가독성 향상
st.markdown("""
    <style>
    .report-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #002147; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .metric-val { font-size: 24px; font-weight: bold; color: #002147; }
    .stTabs [aria-selected="true"] { background-color: #002147 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 전처리 함수 (소수점 제거 해결사)
def clean_df(df):
    for col in ['학번', '반', '호실', '기숙사 호실']:
        if col in df.columns:
            # 문자열로 변환 -> .0 제거 -> 공백 제거
            df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()
    return df

# 3. 날짜 계산
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
target_sat = this_monday + timedelta(days=5)
target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# --- [상단 탭] ---
tab1, tab2 = st.tabs(["📝 학생 신청서 제출", "👨‍🏫 프로 관리자 보고서"])

# ==========================================
# [TAB 1] 학생 신청 화면
# ==========================================
with tab1:
    st.markdown("<h1 style='text-align:center;'>🏫 한일고 40기 신청 시스템 3.0</h1>", unsafe_allow_html=True)
    
    with st.form("apply_form"):
        st.subheader("👤 본인 확인")
        input_sid = st.text_input("학번 4자리", placeholder="예: 1101")
        auth_btn = st.form_submit_button("정보 확인")

    if input_sid:
        try:
            # 마스터 데이터 로드 및 세척
            master_raw = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
            master_df = clean_df(master_raw)
            
            student = master_df[master_df['학번'] == input_sid.strip()]

            if not student.empty:
                s_name = student.iloc[0]['이름']
                s_class = student.iloc[0].get('반', "미지정")
                s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', "미지정"))
                
                st.success(f"✅ 확인되었습니다: **{s_class}반 {s_name}** (기숙사: {s_room})")

                with st.expander("📍 신청 내용 작성", expanded=True):
                    cat = st.radio("구분", ["귀성", "토요외출", "일요외출"], horizontal=True)
                    reason = st.text_input("사유 및 목적지 (5자 이상)")
                    final_submit = st.button("🚀 최종 신청서 제출")

                if final_submit:
                    if len(reason) < 5:
                        st.error("사유를 상세히 입력해 주세요.")
                    else:
                        data_raw = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                        data_df = clean_df(data_raw)
                        
                        if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                            st.warning("⚠️ 이미 이번 주 신청 내역이 있습니다.")
                        else:
                            new_row = pd.DataFrame([{
                                "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "학번": input_sid.strip(), "이름": s_name, "반": s_class, "호실": s_room,
                                "구분": cat, "사유": reason, "대상주말": target_weekend_str
                            }])
                            updated_all = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                            
                            # 3개 시트 동시 업데이트
                            conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_all)
                            this_week = updated_all[updated_all['대상주말'] == target_weekend_str]
                            conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=this_week)
                            stat_df = this_week.groupby('구분').size().reset_index(name='인원수')
                            conn.update(spreadsheet=SHEET_URL, worksheet="통계_현황", data=stat_df)
                            
                            st.success("🎉 신청 완료! 명단이 업데이트되었습니다.")
                            st.balloons()
            else:
                st.error("❌ 명단에 없는 학번입니다.")
        except Exception as e:
            st.error(f"오류: {e}")

# ==========================================
# [TAB 2] 프로 관리자 보고서
# ==========================================
with tab2:
    st.markdown(f"## 📊 {target_weekend_str} 주말 통합 보고서")
    pw = st.text_input("관리자 비밀번호", type="password")
    
    if pw == "hanil40":
        try:
            # 1. 데이터 로드 및 세척
            master_df = clean_df(conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0))
            week_df = clean_df(conn.read(spreadsheet=SHEET_URL, worksheet="이번주_명단", ttl=0))
            
            # --- [섹션 1: 핵심 지표] ---
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("총 신청", f"{len(week_df)}명")
            with c2: st.metric("귀성", f"{len(week_df[week_df['구분']=='귀성'])}명")
            with c3: st.metric("외출(토/일)", f"{len(week_df[week_df['구분'].str.contains('외출')])}명")
            with c4: st.metric("미신청", f"{len(master_df) - len(week_df)}명")
            
            # --- [섹션 2: 프로 분석 보고서] ---
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("<div class='report-card'><h3>🏫 학급별(반) 요약</h3></div>", unsafe_allow_html=True)
                class_sum = week_df.groupby(['반', '구분']).size().unstack(fill_value=0)
                st.dataframe(class_sum, use_container_width=True)
                
            with col_right:
                st.markdown("<div class='report-card'><h3>🏢 기숙사 호실별 요약</h3></div>", unsafe_allow_html=True)
                room_sum = week_df.groupby('호실').size().reset_index(name='인원')
                st.dataframe(room_sum.sort_values(by='인원', ascending=False), use_container_width=True)

            st.markdown("---")
            
            # --- [섹션 3: 미신청자 추적 시스템] ---
            st.markdown("### 🔍 미신청자 추적 (마스터 명단 대조)")
            submitted_ids = week_df['학번'].unique()
            unsubmitted_df = master_df[~master_df['학번'].isin(submitted_ids)][['학번', '이름', '반', '호실']]
            
            if not unsubmitted_df.empty:
                st.warning(f"현재 {len(unsubmitted_df)}명의 학생이 신청하지 않았습니다.")
                st.dataframe(unsubmitted_df.sort_values(by=['반', '학번']), use_container_width=True)
            else:
                st.success("모든 학생이 신청을 완료했습니다!")

            # --- [섹션 4: 전체 명단 및 다운로드] ---
            st.markdown("### 📋 이번 주 상세 명단")
            st.dataframe(week_df.sort_values(by=['반', '학번']), use_container_width=True)
            
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 프로 보고서 다운로드 (Excel/CSV)", csv, f"40기_보고서_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"관리자 로드 오류: {e}")

