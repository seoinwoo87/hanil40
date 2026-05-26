import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# [필수] 구글 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

# 1. 페이지 설정
st.set_page_config(page_title="한일고 40기 통합 관리시스템", page_icon="🏫", layout="centered")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 날짜 및 마감 계산
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

if now < deadline:
    target_sat = deadline + timedelta(days=5) 
    is_open = True
else:
    target_sat = deadline + timedelta(days=12)
    is_open = True

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# --- [TAB 설정] ---
tab1, tab2 = st.tabs(["📝 신청서 제출", "👨‍🏫 선생님 전용 관리자"])

# --- [TAB 1: 신청 화면] ---
with tab1:
    st.markdown("<h1 style='text-align:center;'>🏫 한일고 40기 신청 시스템 2.0</h1>", unsafe_allow_html=True)
    
    with st.form("apply_form"):
        st.subheader("👤 본인 확인")
        sid = st.text_input("학번 (4자리)", placeholder="예: 1101")
        submit_btn = st.form_submit_button("정보 확인 및 신청 계속하기")

    if sid:
        # [핵심] 마스터 데이터 읽기
        try:
            master_df = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
            student_info = master_df[master_df['학번'].astype(str) == sid]
            
            if not student_info.empty:
                name = student_info.iloc[0]['이름']
                s_class = student_info.iloc[0]['반']
                s_room = student_info.iloc[0]['호실']
                
                st.success(f"✅ 확인되었습니다: **{s_class}반 {name} (호실: {s_room})**")
                
                # 추가 입력 필드
                with st.expander("📍 상세 신청 내용 입력", expanded=True):
                    cat = st.radio("신청 구분", ["귀성", "토요외출", "일요외출"], horizontal=True)
                    time_opt = ["토요일 오후", "일요일 오전", "일요일 오후", "기타"]
                    stime = st.selectbox("예정 시간", time_opt)
                    reason = st.text_input("사유 (5자 이상 구체적으로)", placeholder="목적지 및 상세 사유")
                    final_submit = st.button("🚀 최종 제출하기")
                
                if final_submit:
                    if len(reason) < 5:
                        st.error("사유를 구체적으로 적어주세요.")
                    else:
                        # 1. 기존 누적 데이터(data) 업데이트
                        data_df = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                        
                        # 중복 체크
                        if not data_df[(data_df['학번'].astype(str) == sid) & (data_df['대상주말'] == target_weekend_str)].empty:
                            st.warning("⚠️ 이미 이번 주 신청 내역이 존재합니다.")
                        else:
                            new_row = pd.DataFrame([{
                                "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "학번": sid, "이름": name, "반": s_class, "호실": s_room,
                                "구분": cat, "귀가/외출 일시": stime, "사유": reason, "대상주말": target_weekend_str
                            }])
                            
                            # (1) data 탭 업데이트
                            updated_data = pd.concat([data_df, new_row], ignore_index=True).fillna("").astype(str)
                            conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_data)
                            
                            # (2) 이번주_명단 탭 업데이트 (해당 주말 데이터만 필터링해서 덮어쓰기)
                            this_week_full = updated_data[updated_data['대상주말'] == target_weekend_str]
                            conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=this_week_full)
                            
                            # (3) 통계_현황 탭 업데이트
                            stat_df = this_week_full.groupby('구분').size().reset_index(name='인원수')
                            conn.update(spreadsheet=SHEET_URL, worksheet="통계_현황", data=stat_df)
                            
                            st.success("🎉 모든 탭에 성공적으로 기록되었습니다!")
                            st.balloons()
            else:
                st.error("❌ 마스터 명단에 없는 학번입니다. 학번을 다시 확인해 주세요.")
        except Exception as e:
            st.error(f"데이터 연동 오류: {e}")

# --- [TAB 2: 관리자 모드] ---
with tab2:
    st.subheader("👨‍🏫 학년부 관리 도구")
    admin_pw = st.text_input("관리자 비번", type="password")
    if admin_pw == "hanil40":
        # 현재 이번주 명단 바로 보기
        week_df = conn.read(spreadsheet=SHEET_URL, worksheet="이번주_명단", ttl=0)
        st.write(f"### 📊 이번 주 신청 현황 ({target_weekend_str})")
        
        if not week_df.empty:
            # 통계 그래프
            fig = px.bar(week_df.groupby('구분').size().reset_index(name='인원'), x='구분', y='인원', color='구분')
            st.plotly_chart(fig)
            
            # 검색 및 필터
            search = st.text_input("학생 검색 (이름/반/호실)")
            if search:
                week_df = week_df[week_df.astype(str).apply(lambda x: x.str.contains(search)).any(axis=1)]
            
            st.dataframe(week_df, use_container_width=True)
            
            # 다운로드
            csv = week_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 이번 주 명단 다운로드", csv, f"명단_{target_weekend_str}.csv")

부장님, 이 코드가 적용되면 이제 학생이 학번만 쳐도 부장님이 원하시던 **반/번호/기숙사 호실**이 자동으로 따라붙고, 구글 시트의 **모든 탭(`data`, `이번주_명단`, `통계_현황`)이 동시에 숨 쉬듯 업데이트**될 것입니다.

운영해 보시고 보고서 양식에 더 필요한 열이 있다면 언제든 말씀해 주세요!_
