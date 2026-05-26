import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 필수 설정 (부장님 시트 주소)
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 관리시스템 v3.8", page_icon="🏫", layout="wide")

# 디자인: 완전 중앙 집중형 레이아웃
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #f1f5f9; }

    /* 화면 중앙 800px 고정 */
    .main .block-container {
        max-width: 800px;
        padding-top: 2rem;
        margin: 0 auto;
    }

    /* 주간 배너 */
    .main-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc; padding: 40px 20px; border-radius: 20px;
        text-align: center; margin-bottom: 30px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    .banner-main { font-size: 2.2rem; font-weight: 800; color: #deff9a; line-height: 1.3; }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    .stTabs [aria-selected="true"] { font-weight: 700; color: #0f172a !important; }

    /* 입력 섹션 구분선 */
    .section-header {
        border-left: 5px solid #deff9a; padding-left: 15px; 
        font-weight: 700; font-size: 1.2rem; margin: 20px 0 15px 0;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def clean_data(df):
    for col in ['학번', '반', '호실', '기숙사 호실']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df[col] = df[col].replace('nan', '')
    return df

# 날짜 계산
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)
if now < deadline:
    target_sat = deadline + timedelta(days=5)
else:
    target_sat = deadline + timedelta(days=12)
target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# --- [상단 배너] ---
st.markdown(f"""
    <div class="main-banner">
        <div style="opacity: 0.7; letter-spacing: 2px; margin-bottom: 10px;">HANIL HIGH SCHOOL GRADE 40</div>
        <div class="banner-main">{target_weekend_str}<br>귀성/외출 통합 신청</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 학생 신청", "👨‍🏫 교사용"])

# ==========================================
# [TAB 1] 학생 신청 (오류 수정됨)
# ==========================================
with tab1:
    # 폼 시작
    with st.form("unified_form"):
        st.markdown('<div class="section-header">1. 본인 정보 입력</div>', unsafe_allow_html=True)
        input_sid = st.text_input("학번 4자리", placeholder="예: 1101")
        
        st.markdown('<div class="section-header">2. 신청 내용 작성</div>', unsafe_allow_html=True)
        cat = st.radio("신청 종류", ["귀성", "외출"], horizontal=True)
        stime = st.selectbox("예정 시간", ["토요일 오후", "일요일 오전", "일요일 오후", "기타"])
        detailed_time = st.text_input("상세 시간 (기타 선택 시만 입력)", placeholder="예: 토요일 15:00")
        base_reason = st.text_input("구 구체적 사유 (5자 이상)")
        
        # 폼의 모든 구성 요소 뒤에 마지막으로 버튼 배치
        submit_btn = st.form_submit_button("🚀 신청서 제출하기")

    if submit_btn:
        if not input_sid:
            st.error("학번을 입력해주세요.")
        elif len(base_reason) < 5:
            st.error("사유를 5자 이상 입력해주세요.")
        elif stime == "기타" and not detailed_time:
            st.error("기타 시간 선택 시 상세 시간을 적어주세요.")
        else:
            try:
                # 마스터 데이터 대조
                master_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0))
                student = master_df[master_df['학번'] == input_sid.strip()]

                if not student.empty:
                    s_name = student.iloc[0]['이름']
                    s_class = student.iloc[0].get('반', "-")
                    s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', "-"))
                    
                    # 데이터 저장
                    data_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all"))
                    
                    if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                        st.warning("⚠️ 이미 신청된 내역이 있습니다.")
                    else:
                        final_reason = f"[{detailed_time}] {base_reason}" if stime == "기타" else base_reason
                        new_row = pd.DataFrame([{
                            "신청시간": datetime.now().strftime("%m-%d %H:%M"),
                            "학번": input_sid.strip(), "이름": s_name, "반": s_class, "호실": s_room,
                            "구분": cat, "귀가/외출 일시": stime, "사유": final_reason, "대상주말": target_weekend_str
                        }])
                        
                        updated_all = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                        conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_all)
                        conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=updated_all[updated_all['대상주말'] == target_weekend_str])
                        
                        st.balloons()
                        st.success(f"✅ {s_name} 학생, 신청이 완료되었습니다!")
                else:
                    st.error("❌ 학번을 다시 확인해주세요 (명단에 없음).")
            except Exception as e:
                st.error(f"오류 발생: {e}")

# ==========================================
# [TAB 2] 교사용 (호실별 통계 포함)
# ==========================================
with tab2:
    admin_pw = st.text_input("교사용 암호", type="password")
    if admin_pw == "hanil40":
        try:
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            week_df = full_data[full_data['대상주말'] == target_weekend_str]

            st.markdown(f"#### 📊 {target_weekend_str} 요약")
            c1, c2, c3 = st.columns(3)
            c1.metric("총 신청", f"{len(week_df)}명")
            c2.metric("귀성", f"{len(week_df[week_df['구분']=='귀성'])}명")
            c3.metric("외출", f"{len(week_df[week_df['구분']=='외출'])}명")

            st.markdown('<div class="section-header">🏫 학급별 통계</div>', unsafe_allow_html=True)
            if not week_df.empty:
                st.table(week_df.groupby(['반', '구분']).size().unstack(fill_value=0))
            
            st.markdown('<div class="section-header">🏢 호실별 통계</div>', unsafe_allow_html=True)
            if not week_df.empty:
                room_stat = week_df.groupby(['호실', '구분']).size().unstack(fill_value=0)
                st.dataframe(room_stat, use_container_width=True)

            st.markdown('<div class="section-header">📋 전체 신청 명단</div>', unsafe_allow_html=True)
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 명단 다운로드 (CSV)", csv, f"40기_신청명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터 로드 오류: {e}")
