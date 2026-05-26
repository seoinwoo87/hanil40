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
        background: linear-gradient(135deg, #002147 0%, #003366 100%);
        color: white; padding: 30px; border-radius: 15px;
        text-align: center; margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .week-title { font-size: 1.1rem; opacity: 0.9; margin-bottom: 5px; }
    .week-date { font-size: 2rem; font-weight: 800; color: #deff9a; }
    
    /* 카드 스타일 */
    .admin-card {
        background: white; padding: 20px; border-radius: 12px;
        border-top: 5px solid #002147; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; }
    .stTabs [aria-selected="true"] { background-color: #002147 !important; color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 데이터 세척 함수 (소수점 제거)
# ==========================================
def clean_data(df):
    for col in ['학번', '반', '호실', '기숙사 호실']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df[col] = df[col].replace('nan', '')
    return df

# ==========================================
# 3. 날짜 계산 (대상 주말)
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
        <div style="font-size: 0.85rem; margin-top: 10px; opacity: 0.8;">현재 위 주말에 대한 신청을 접수 중입니다.</div>
    </div>
    """, unsafe_allow_html=True)

# 탭 이름 변경: 관리자보고서 -> 교사용
tab1, tab2 = st.tabs(["📝 학생 신청 제출", "👨‍🏫 교사용"])

# ==========================================
# [TAB 1] 학생 신청
# ==========================================
with tab1:
    with st.form("auth_form"):
        st.markdown("### 1. 학생 확인")
        input_sid = st.text_input("학번 4자리", placeholder="예: 1101")
        auth_btn = st.form_submit_button("정보 확인")

    if input_sid:
        try:
            master_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0))
            student = master_df[master_df['학번'] == input_sid.strip()]

            if not student.empty:
                s_name = student.iloc[0]['이름']
                s_class = student.iloc[0].get('반', "-")
                s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', "-"))
                
                st.success(f"✅ **{s_class}반 {s_name}** 확인 (호실: {s_room}호)")

                with st.expander("📝 신청 내용 작성", expanded=True):
                    cat = st.radio("구분", ["귀성", "토요외출", "일요외출"], horizontal=True)
                    reason = st.text_input("사유 (5자 이상)")
                    final_submit = st.button("🚀 신청 완료")

                if final_submit:
                    if len(reason) < 5:
                        st.error("사유를 조금 더 자세히 적어주세요.")
                    else:
                        data_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all"))
                        
                        if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                            st.warning("⚠️ 이미 이번 주말 신청 내역이 존재합니다.")
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
                            st.success(f"🎉 신청이 정상적으로 완료되었습니다.")
            else:
                st.error("❌ 학번이 명단에 없습니다. 다시 확인해 주세요.")
        except Exception as e:
            st.error(f"오류 발생: {e}")

# ==========================================
# [TAB 2] 교사용 (미신청 추적 삭제 및 요약 집중)
# ==========================================
with tab2:
    admin_pw = st.text_input("교사용 암호", type="password")
    if admin_pw == "hanil40":
        try:
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            week_df = full_data[full_data['대상주말'] == target_weekend_str]

            # 1. 상단 간단 통계
            st.markdown(f"### 📊 {target_weekend_str} 신청 현황")
            m1, m2, m3 = st.columns(3)
            m1.metric("총 신청 인원", f"{len(week_df)}명")
            m2.metric("귀성 인원", f"{len(week_df[week_df['구분']=='귀성'])}명")
            m3.metric("외출 인원", f"{len(week_df[week_df['구분'].str.contains('외출')])}명")

            # 2. 학급별/호실별 요약
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div class='admin-card'><h4>🏫 학급별 요약</h4></div>", unsafe_allow_html=True)
                if not week_df.empty:
                    st.dataframe(week_df.groupby(['반', '구분']).size().unstack(fill_value=0), use_container_width=True)
            with col2:
                st.markdown("<div class='admin-card'><h4>🏢 호실별 인원</h4></div>", unsafe_allow_html=True)
                if not week_df.empty:
                    st.dataframe(week_df.groupby('호실').size().reset_index(name='명').sort_values('명', ascending=False), use_container_width=True, hide_index=True)

            # 3. 전체 명단
            st.markdown("### 📋 이번 주 전체 신청 명단")
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            # 4. 다운로드
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 명단 엑셀(CSV) 다운로드", csv, f"40기_신청명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터를 불러올 수 없습니다: {e}")
