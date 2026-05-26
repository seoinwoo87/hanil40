import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 필수 설정 (부장님 시트 주소)
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 관리시스템 v3.6", page_icon="🏫", layout="wide")

# 디자인: 화면 중앙 집중형 레이아웃 및 스타일 정의
st.markdown("""
    <style>
    /* 전체 배경색 */
    .stApp { background-color: #f8fafc; }
    
    /* 화면 정중앙으로 모아주는 핵심 컨테이너 (너비 700px 제한) */
    [data-testid="stVerticalBlock"] > div:has(div.centered-content) {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    
    .centered-content {
        max-width: 700px;
        width: 100%;
        margin: 0 auto;
    }
    
    /* 주간 배너 디자인 */
    .main-banner {
        background: linear-gradient(135deg, #001a33 0%, #003366 100%);
        color: white; padding: 40px 20px; border-radius: 20px;
        text-align: center; margin-bottom: 30px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    .banner-sub { font-size: 1rem; opacity: 0.8; margin-bottom: 10px; letter-spacing: 2px; }
    .banner-main { font-size: 2.2rem; font-weight: 800; color: #deff9a; line-height: 1.2; }
    
    /* 폼/카드 섹션 디자인 */
    .stForm, .info-card {
        background: white !important; padding: 30px !important; border-radius: 15px !important;
        border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.02) !important;
    }
    
    /* 탭 메뉴 중앙 정렬 */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; justify-content: center; }
    .stTabs [aria-selected="true"] { font-weight: bold; color: #001a33 !important; border-bottom: 3px solid #001a33 !important; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 데이터 세척 함수 (이름 오류 수정: clean_data)
# ==========================================
def clean_data(df):
    for col in ['학번', '반', '호실', '기숙사 호실']:
        if col in df.columns:
            # 소수점 제거 및 공백 정리
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df[col] = df[col].replace('nan', '')
    return df

# ==========================================
# 3. 날짜 및 신청 주간 계산
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

# --- [메인 레이아웃 시작] ---
# 모든 내용을 centered-content 클래스로 감싸서 가운데로 모읍니다.
st.markdown('<div class="centered-content">', unsafe_allow_html=True)

st.markdown(f"""
    <div class="main-banner">
        <div class="banner-sub">HANIL HIGH SCHOOL GRADE 40</div>
        <div class="banner-main">{target_weekend_str}<br>귀성/외출 신청</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 학생용 신청창", "👨‍🏫 교사용 관리창"])

# ==========================================
# [TAB 1] 학생용 신청창
# ==========================================
with tab1:
    with st.form("student_form"):
        st.markdown("#### 🔍 학생 정보 확인")
        input_sid = st.text_input("학번 4자리 입력", placeholder="예: 1101")
        check_btn = st.form_submit_button("정보 확인하기")

    if input_sid:
        try:
            master_raw = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
            master_df = clean_data(master_raw) # 함수 이름 수정 완료
            student = master_df[master_df['학번'] == input_sid.strip()]

            if not student.empty:
                s_name = student.iloc[0]['이름']
                s_class = student.iloc[0].get('반', "-")
                s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', "-"))
                
                st.success(f"✅ 확인되었습니다: **{s_class}반 {s_name}** (호실: {s_room})")

                with st.expander("📝 신청 내용 입력", expanded=True):
                    # 1. 구분 단순화
                    cat = st.radio("신청 구분", ["귀성", "외출"], horizontal=True)
                    
                    # 2. 시간 선택 및 기타 입력
                    time_opt = ["토요일 오후", "일요일 오전", "일요일 오후", "기타"]
                    stime = st.selectbox("예정 시간 선택", time_opt)
                    
                    detailed_time = ""
                    if stime == "기타":
                        detailed_time = st.text_input("상세 시간을 입력하세요 (예: 토요일 15:00)")
                    
                    # 사유 입력
                    base_reason = st.text_input("구체적 사유 (5자 이상)")
                    final_submit = st.button("🚀 신청 완료하기")

                if final_submit:
                    if len(base_reason) < 5:
                        st.error("사유를 조금 더 자세히 적어주세요.")
                    elif stime == "기타" and not detailed_time:
                        st.error("기타 선택 시 시간을 직접 입력해야 합니다.")
                    else:
                        data_raw = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                        data_df = clean_data(data_raw)
                        
                        if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                            st.warning("⚠️ 이미 이번 주 신청 내역이 존재합니다.")
                        else:
                            # 사유에 기타 시간 병합
                            final_reason = f"[{detailed_time}] {base_reason}" if stime == "기타" else base_reason
                            
                            new_row = pd.DataFrame([{
                                "신청시간": datetime.now().strftime("%m-%d %H:%M"),
                                "학번": input_sid.strip(), "이름": s_name, "반": s_class, "호실": s_room,
                                "구분": cat, "귀가/외출 일시": stime, "사유": final_reason, "대상주말": target_weekend_str
                            }])
                            
                            updated_all = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                            conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_all)
                            
                            # '이번주_명단' 시트 갱신
                            this_week = updated_all[updated_all['대상주말'] == target_weekend_str]
                            conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=this_week)
                            
                            st.balloons()
                            st.success("✅ 신청이 완료되었습니다. 안전하게 다녀오세요!")
            else:
                st.error("❌ 등록되지 않은 학번입니다. 학년부에 문의하세요.")
        except Exception as e:
            st.error(f"시스템 오류: {e}")

# ==========================================
# [TAB 2] 교사용 관리창
# ==========================================
with tab2:
    admin_pw = st.text_input("교사용 인증 코드", type="password")
    if admin_pw == "hanil40":
        try:
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            week_df = full_data[full_data['대상주말'] == target_weekend_str]

            st.markdown(f"#### 📊 {target_weekend_str} 현황")
            c1, c2, c3 = st.columns(3)
            c1.metric("총 인원", f"{len(week_df)}명")
            c2.metric("귀성", f"{len(week_df[week_df['구분']=='귀성'])}명")
            c3.metric("외출", f"{len(week_df[week_df['구분']=='외출'])}명")

            st.markdown("---")
            st.markdown("##### 🏫 학급별 요약")
            if not week_df.empty:
                st.table(week_df.groupby(['반', '구분']).size().unstack(fill_value=0))
            
            st.markdown("##### 📋 상세 신청 명단")
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 명단 다운로드 (CSV)", csv, f"40기_신청명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터를 불러올 수 없습니다: {e}")

st.markdown('</div>', unsafe_allow_html=True) # centered-content 종료
