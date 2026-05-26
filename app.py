import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# [필수] 구글 시트 주소 (data 탭 주소)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

# 1. 페이지 설정
st.set_page_config(page_title="한일고 40기 귀성/외출 신청", page_icon="🏫", layout="centered")

# 디자인 CSS
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #f0f2f6;
        border-radius: 10px 10px 0px 0px; gap: 1px; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #002147; color: white; }
    .main-title { text-align: center; color: #002147; font-size: 2.2em; font-weight: 800; padding: 20px; }
    .status-box { background: linear-gradient(135deg, #002147 0%, #003366 100%); color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 날짜 계산
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

if now < deadline:
    target_sat = deadline + timedelta(days=5) 
else:
    target_sat = deadline + timedelta(days=12)

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# --- [상단 탭 분리] ---
tab1, tab2 = st.tabs(["📝 신청서 제출", "👨‍🏫 관리자 모드"])

# --- [TAB 1: 학생 신청 화면] ---
with tab1:
    st.markdown('<h1 class="main-title">🏫 한일고 40기 신청 시스템</h1>', unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="status-box">
            <p style="margin:0; opacity:0.8;">현재 신청 주말</p>
            <p style="font-size:1.6em; margin:5px 0;"><b>{target_weekend_str}</b></p>
        </div>
        """, unsafe_allow_html=True)

    with st.container():
        st.subheader("👤 학생 정보")
        c1, c2 = st.columns(2)
        sid = c1.text_input("학번 (4자리)", placeholder="예: 1101", key="s_id")
        sname = c2.text_input("성명", placeholder="실명", key="s_name")
        
        st.markdown("---")
        st.subheader("📍 신청 내용")
        cat = st.radio("구분", ["귀성", "토요외출", "일요외출"], horizontal=True)
        
        c3, c4 = st.columns(2)
        time_opt = ["토요일 오후", "일요일 오전", "일요일 오후", "기타"]
        stime = c3.selectbox("예정 시간", time_opt)
        final_time = stime
        if stime == "기타":
            final_time = st.text_input("상세 시간")
            
        reason = c4.text_input("사유 및 목적지 (필수)", placeholder="5자 이상 구체적으로")
        
        confirm = st.checkbox("본인 신청임을 확인합니다.")

    if st.button("🚀 신청서 제출하기"):
        if not (sid.isdigit() and len(sid) == 4): st.error("학번 4자리를 확인하세요.")
        elif not sname: st.error("이름을 입력하세요.")
        elif not reason or len(reason) < 5: st.error("사유를 구체적으로(5자 이상) 적어주세요.")
        elif not confirm: st.warning("확인 체크박스를 선택하세요.")
        else:
            try:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                new_data = pd.DataFrame([{
                    "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "학번": sid, "이름": sname, "구분": cat, 
                    "귀가/외출 일시": final_time, "사유": reason, "대상주말": target_weekend_str
                }])
                updated_df = pd.concat([df, new_data], ignore_index=True).fillna("").astype(str)
                conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_df)
                st.success("🎉 접수되었습니다!")
                st.balloons()
            except Exception as e:
                st.error(f"저장 실패: {e}")

# --- [TAB 2: 선생님 전용 관리자 모드] ---
with tab2:
    st.markdown("<h2 style='text-align:center;'>👨‍🏫 학년부 관리 시스템</h2>", unsafe_allow_html=True)
    pw = st.text_input("관리자 비밀번호", type="password")
    
    if pw == "hanil40":
        try:
            # 전체 데이터 읽기
            admin_df = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
            
            # [필터링] 이번 주말 데이터만 추출
            this_week_df = admin_df[admin_df["대상주말"] == target_weekend_str]
            
            # --- [통계 영역] ---
            st.markdown(f"### 📊 이번 주 신청 현황 ({target_weekend_str})")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("전체 신청", f"{len(this_week_df)}건")
            m2.metric("귀성", f"{len(this_week_df[this_week_df['구분']=='귀성'])}건")
            m3.metric("토요외출", f"{len(this_week_df[this_week_df['구분']=='토요외출'])}건")
            m4.metric("일요외출", f"{len(this_week_df[this_week_df['구분']=='일요외출'])}건")
            
            st.markdown("---")
            
            # --- [명단 출력] ---
            st.write("#### 📋 상세 명단 (최신순)")
            # 최신 신청자가 위로 오게 정렬
            this_week_df = this_week_df.sort_index(ascending=False)
            st.dataframe(this_week_df, use_container_width=True)
            
            # 엑셀 다운로드 버튼 (선생님들 보고용)
            csv = this_week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 이번 주 명단 다운로드(CSV)", data=csv, file_name=f"hanil40_{target_weekend_str}.csv", mime='text/csv')

            with st.expander("📁 전체 누적 데이터 보기 (전체 기간)"):
                st.dataframe(admin_df)
                
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
