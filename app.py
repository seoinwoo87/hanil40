import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 필수 설정 (부장님 시트 주소)
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 관리시스템 v3.7", page_icon="🏫", layout="wide")

# 디자인: 완전 중앙 집중형 레이아웃 및 심미적 디자인 정의
st.markdown("""
    <style>
    /* 전체 배경 및 폰트 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #f1f5f9; }

    /* 화면 중앙 고정 로직 (가장 중요) */
    .main .block-container {
        max-width: 800px;
        padding-left: 1rem;
        padding-right: 1rem;
        margin: 0 auto;
    }

    /* 주간 배너 디자인 */
    .main-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc; padding: 45px 20px; border-radius: 24px;
        text-align: center; margin-bottom: 35px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    .banner-sub { font-size: 0.95rem; opacity: 0.7; margin-bottom: 12px; letter-spacing: 3px; font-weight: 300; }
    .banner-main { font-size: 2.3rem; font-weight: 800; color: #deff9a; line-height: 1.3; }
    
    /* 탭 스타일 최적화 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #ffffff; border-radius: 10px 10px 0 0;
        padding: 10px 30px; border: 1px solid #e2e8f0; border-bottom: none;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #0f172a !important; color: #deff9a !important; font-weight: 700;
    }

    /* 카드/폼 디자인 */
    .stForm, .info-card {
        background: white !important; padding: 30px !important; border-radius: 20px !important;
        border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
        margin-bottom: 20px;
    }
    h4 { color: #0f172a; border-left: 5px solid #deff9a; padding-left: 15px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def clean_data(df):
    for col in ['학번', '반', '호실', '기숙사 호실']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df[col] = df[col].replace('nan', '')
    return df

# 날짜 및 신청 주간 계산
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

if now < deadline:
    target_sat = deadline + timedelta(days=5)
else:
    target_sat = deadline + timedelta(days=12)

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# --- [메인 레이아웃 시작] ---
st.markdown(f"""
    <div class="main-banner">
        <div class="banner-sub">HANIL HIGH SCHOOL GRADE 40</div>
        <div class="banner-main">{target_weekend_str}<br>귀성/외출 신청</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 학생 신청", "👨‍🏫 교사용 관리"])

# ==========================================
# [TAB 1] 학생용 신청창
# ==========================================
with tab1:
    with st.form("student_form"):
        st.markdown("#### 👤 학생 정보 확인")
        input_sid = st.text_input("학번 4자리 입력", placeholder="예: 1101")
        check_btn = st.form_submit_button("정보 확인")

    if input_sid:
        try:
            master_raw = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
            master_df = clean_data(master_raw)
            student = master_df[master_df['학번'] == input_sid.strip()]

            if not student.empty:
                s_name = student.iloc[0]['이름']
                s_class = student.iloc[0].get('반', "-")
                s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', "-"))
                
                st.success(f"✅ **{s_class}반 {s_name}** 학생 확인되었습니다.")

                with st.expander("📝 세부 신청 내용 작성", expanded=True):
                    cat = st.radio("구분", ["귀성", "외출"], horizontal=True)
                    
                    time_opt = ["토요일 오후", "일요일 오전", "일요일 오후", "기타"]
                    stime = st.selectbox("예정 시간", time_opt)
                    
                    detailed_time = ""
                    if stime == "기타":
                        detailed_time = st.text_input("상세 시간 직접 입력", placeholder="예: 토요일 15:00")
                    
                    base_reason = st.text_input("사유 및 목적지 (5자 이상)")
                    final_submit = st.form_submit_button("🚀 최종 신청서 제출") # 폼 안의 버튼으로 변경

                if final_submit:
                    if len(base_reason) < 5:
                        st.error("사유를 조금 더 구체적으로 적어주세요.")
                    elif stime == "기타" and not detailed_time:
                        st.error("기타 선택 시 시간을 입력해야 합니다.")
                    else:
                        data_raw = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                        data_df = clean_data(data_raw)
                        
                        if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                            st.warning("⚠️ 이미 이번 주 신청 내역이 있습니다.")
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
                            st.success("✅ 신청 완료! 안전하게 다녀오세요.")
            else:
                st.error("❌ 명단에 없는 학번입니다.")
        except Exception as e:
            st.error(f"시스템 오류: {e}")

# ==========================================
# [TAB 2] 교사용 관리창
# ==========================================
with tab2:
    admin_pw = st.text_input("관리자 암호", type="password")
    if admin_pw == "hanil40":
        try:
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            week_df = full_data[full_data['대상주말'] == target_weekend_str]

            st.markdown(f"#### 📊 {target_weekend_str} 현황 요약")
            c1, c2, c3 = st.columns(3)
            c1.metric("총 신청", f"{len(week_df)}명")
            c2.metric("귀성", f"{len(week_df[week_df['구분']=='귀성'])}명")
            c3.metric("외출", f"{len(week_df[week_df['구분']=='외출'])}명")

            # 1. 학급별 통계
            st.markdown("#### 🏫 학급별 통계")
            if not week_df.empty:
                class_sum = week_df.groupby(['반', '구분']).size().unstack(fill_value=0)
                st.table(class_sum)
            
            # 2. 호실별 통계 (부장님 요청사항 복구)
            st.markdown("#### 🏢 호실별 신청 현황")
            if not week_df.empty:
                room_sum = week_df.groupby(['호실', '구분']).size().unstack(fill_value=0)
                st.dataframe(room_sum, use_container_width=True)

            # 3. 상세 명단
            st.markdown("#### 📋 상세 명단 (전체)")
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 명단 다운로드 (CSV)", csv, f"40기_신청명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터 로드 오류: {e}")
