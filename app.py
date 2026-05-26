import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 필수 설정
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 관리시스템 v3.9", page_icon="🏫", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #f1f5f9; }

    /* 중앙 800px 고정 */
    .main .block-container {
        max-width: 800px;
        padding-top: 2rem;
        margin: 0 auto;
    }

    .main-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc; padding: 40px 20px; border-radius: 20px;
        text-align: center; margin-bottom: 30px;
    }
    .banner-main { font-size: 2.1rem; font-weight: 800; color: #deff9a; }
    
    .section-header {
        border-left: 5px solid #deff9a; padding-left: 15px; 
        font-weight: 700; font-size: 1.1rem; margin: 25px 0 15px 0;
        color: #0f172a;
    }
    
    /* 표 안의 숫자 정렬을 위한 스타일 */
    [data-testid="stMetricValue"] { text-align: center; }
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

# --- 배너 ---
st.markdown(f"""
    <div class="main-banner">
        <div style="opacity: 0.7; letter-spacing: 2px; margin-bottom: 10px;">HANIL HIGH SCHOOL GRADE 40</div>
        <div class="banner-main">{target_weekend_str}<br>귀성/외출 신청 현황</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 학생 신청", "👨‍🏫 교사용 관리"])

# ==========================================
# [TAB 1] 학생 신청
# ==========================================
with tab1:
    with st.form("unified_form"):
        st.markdown('<div class="section-header">1. 정보 확인 및 신청</div>', unsafe_allow_html=True)
        input_sid = st.text_input("학번 4자리", placeholder="예: 1101")
        cat = st.radio("신청 종류", ["귀성", "외출"], horizontal=True)
        stime = st.selectbox("예정 시간", ["토요일 오후", "일요일 오전", "일요일 오후", "기타"])
        detailed_time = st.text_input("상세 시간 (기타 선택 시만)", placeholder="예: 토요일 15:00")
        base_reason = st.text_input("구체적 사유 (5자 이상)")
        submit_btn = st.form_submit_button("🚀 신청서 제출하기")

    if submit_btn:
        if not input_sid or len(base_reason) < 5:
            st.error("학번과 사유(5자 이상)를 정확히 입력해주세요.")
        else:
            try:
                master_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0))
                student = master_df[master_df['학번'] == input_sid.strip()]

                if not student.empty:
                    s_name = student.iloc[0]['이름']
                    data_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all"))
                    
                    if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                        st.warning("⚠️ 이미 신청 내역이 존재합니다.")
                    else:
                        final_reason = f"[{detailed_time}] {base_reason}" if stime == "기타" else base_reason
                        new_row = pd.DataFrame([{
                            "신청시간": datetime.now().strftime("%m-%d %H:%M"),
                            "학번": input_sid.strip(), "이름": s_name, "반": student.iloc[0].get('반', "-"), 
                            "호실": student.iloc[0].get('호실', "-"), "구분": cat, 
                            "귀가/외출 일시": stime, "사유": final_reason, "대상주말": target_weekend_str
                        }])
                        updated_all = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                        conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_all)
                        conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=updated_all[updated_all['대상주말'] == target_weekend_str])
                        st.balloons()
                        st.success(f"✅ {s_name} 학생, 신청 완료!")
                else:
                    st.error("❌ 등록되지 않은 학번입니다.")
            except Exception as e:
                st.error(f"오류: {e}")

# ==========================================
# [TAB 2] 교사용 (정렬 및 통계 강화)
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

            # 통계 작성을 위한 보조 함수 (컬럼 고정 및 정렬)
            def get_stat_df(df, group_col):
                if df.empty: return pd.DataFrame()
                stat = df.groupby([group_col, '구분']).size().unstack(fill_value=0)
                # '귀성'과 '외출' 컬럼이 없어도 0으로 생성하여 표 형식 유지
                for col in ["귀성", "외출"]:
                    if col not in stat.columns:
                        stat[col] = 0
                return stat[["귀성", "외출"]] # 순서 고정

            # 1. 학급별 통계 (가운데 정렬 적용)
            st.markdown('<div class="section-header">🏫 학급별 통계</div>', unsafe_allow_html=True)
            class_stat = get_stat_df(week_df, '반')
            if not class_stat.empty:
                st.dataframe(class_stat, use_container_width=True, 
                             column_config={col: st.column_config.NumberColumn(format="%d", help=f"{col} 인원", width="small") for col in class_stat.columns})

            # 2. 호실별 통계 (가운데 정렬 적용)
            st.markdown('<div class="section-header">🏢 호실별 통계</div>', unsafe_allow_html=True)
            room_stat = get_stat_df(week_df, '호실')
            if not room_stat.empty:
                st.dataframe(room_stat, use_container_width=True,
                             column_config={col: st.column_config.NumberColumn(format="%d", width="small") for col in room_stat.columns})

            st.markdown('<div class="section-header">📋 전체 명단</div>', unsafe_allow_html=True)
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 CSV 다운로드", csv, f"40기_신청명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터 로드 오류: {e}")
