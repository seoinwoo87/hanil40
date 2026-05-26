import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 필수 설정
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="Hanil High School 40th", page_icon="🏫", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@500;700;900&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Noto Sans KR', sans-serif; 
        font-weight: 700 !important;
        color: #0f172a;
    }
    .stApp { background-color: #f8fafc; }

    .main .block-container {
        max-width: 750px;
        padding-top: 2rem;
        margin: 0 auto;
    }

    .main-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff; padding: 45px 20px; border-radius: 20px;
        text-align: center; margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .banner-sub { font-size: 1.1rem; font-weight: 900; color: #cbd5e1; margin-bottom: 12px; letter-spacing: 2px; }
    .banner-main { font-size: 2.3rem; font-weight: 900; color: #deff9a; }
    
    .section-header {
        background-color: #e2e8f0;
        border-left: 8px solid #0f172a;
        padding: 12px 18px;
        font-weight: 900;
        font-size: 1.2rem;
        margin: 30px 0 15px 0;
        border-radius: 0 10px 10px 0;
    }

    /* 경고 문구 스타일 */
    .warning-text {
        color: #e11d48;
        font-size: 0.95rem;
        font-weight: 800;
        margin-top: 10px;
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

# --- 상단 배너 ---
st.markdown(f"""
    <div class="main-banner">
        <div class="banner-sub">HANIL HIGH SCHOOL 40TH</div>
        <div class="banner-main">{target_weekend_str}<br>귀성/외출 신청</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 학생 신청", "👨‍🏫 교사용 관리"])

# ==========================================
# [TAB 1] 학생 신청 (입력 제어 및 장난 방지)
# ==========================================
with tab1:
    st.markdown('<div class="section-header">본인 확인 및 내용 작성</div>', unsafe_allow_html=True)
    
    # 1. 기본 정보 입력
    input_sid = st.text_input("학번 4자리 (예: 1101)")
    cat = st.radio("신청 종류", ["귀성", "외출"], horizontal=True)
    stime = st.selectbox("예정 시간 선택", ["토요일 오후", "일요일 오전", "일요일 오후", "기타"])
    
    # [수정 사항] '기타' 선택 시에만 상세 시간 입력창 표시
    detailed_time = ""
    if stime == "기타":
        detailed_time = st.text_input("📍 상세 시간을 직접 입력하세요 (예: 토요일 15:00)")
    
    base_reason = st.text_input("구체적 사유 (목적지 포함 5자 이상)")

    st.markdown("---")
    
    # [장난 방지 핵심 방안] 최종 확인 섹션
    st.markdown('<p class="warning-text">⚠️ 주의: 허위 신청이나 타인 학번 도용 시 학생 생활 규정에 따라 불이익을 받을 수 있습니다.</p>', unsafe_allow_html=True)
    
    # 제출 전 확인용 체크박스
    confirm_check = st.checkbox("위 신청 내용이 본인의 것이며 사실임을 확인합니다.")
    
    # 체크박스를 눌러야만 버튼 활성화
    submit_btn = st.button("🚀 신청서 최종 제출하기", disabled=not confirm_check)

    if submit_btn:
        if not input_sid or len(base_reason) < 5:
            st.error("학번과 사유를 정확히 입력해주세요.")
        elif stime == "기타" and not detailed_time:
            st.error("기타 시간 선택 시 상세 시간을 입력해야 합니다.")
        else:
            try:
                master_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0))
                student = master_df[master_df['학번'] == input_sid.strip()]

                if not student.empty:
                    s_name = student.iloc[0]['이름']
                    data_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all"))
                    
                    # 중복 체크
                    if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == target_weekend_str)].empty:
                        st.warning(f"⚠️ {s_name} 학생은 이미 신청 내역이 존재합니다.")
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
                        st.success(f"✅ {s_name} 학생, 신청이 완료되었습니다!")
                else:
                    st.error("❌ 등록되지 않은 학번입니다. 본인의 학번을 확인하세요.")
            except Exception as e:
                st.error(f"오류: {e}")

# ==========================================
# [TAB 2] 교사용 관리
# ==========================================
with tab2:
    admin_pw = st.text_input("교사용 비밀번호", type="password")
    if admin_pw == "hanil40":
        try:
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            week_df = full_data[full_data['대상주말'] == target_weekend_str]

            st.markdown(f"#### 📊 {target_weekend_str} 요약 통계")
            c1, c2, c3 = st.columns(3)
            c1.metric("총 인원", f"{len(week_df)}명")
            c2.metric("귀성", f"{len(week_df[week_df['구분']=='귀성'])}명")
            c3.metric("외출", f"{len(week_df[week_df['구분']=='외출'])}명")

            def make_stat(df, idx):
                if df.empty: return pd.DataFrame()
                s = df.groupby([idx, '구분']).size().unstack(fill_value=0)
                for c in ["귀성", "외출"]:
                    if c not in s.columns: s[c] = 0
                s['합계'] = s["귀성"] + s["외출"]
                return s[["귀성", "외출", "합계"]]

            conf = {
                "귀성": st.column_config.NumberColumn("귀성", format="%d", width="small"),
                "외출": st.column_config.NumberColumn("외출", format="%d", width="small"),
                "합계": st.column_config.NumberColumn("합계", format="%d", width="small"),
            }

            st.markdown('<div class="section-header">🏫 학급별 현황</div>', unsafe_allow_html=True)
            class_stat = make_stat(week_df, '반')
            if not class_stat.empty:
                st.dataframe(class_stat, width=400, column_config=conf)

            st.markdown('<div class="section-header">🏢 호실별 현황</div>', unsafe_allow_html=True)
            room_stat = make_stat(week_df, '호실')
            if not room_stat.empty:
                st.dataframe(room_stat, width=400, column_config=conf)

            st.markdown('<div class="section-header">📋 금주 전체 명단</div>', unsafe_allow_html=True)
            st.dataframe(week_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 명단 다운로드 (CSV)", csv, f"40기_명단_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
