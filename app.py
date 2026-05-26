import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# [필수] 부장님 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 통합 관리시스템", page_icon="🏫", layout="centered")
conn = st.connection("gsheets", type=GSheetsConnection)

# 날짜 계산
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
target_sat = this_monday + (timedelta(days=5) if now.weekday() < 0 else timedelta(days=5)) # 예시 로직
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ 신청분"

tab1, tab2 = st.tabs(["📝 신청서 제출", "👨‍🏫 선생님 전용 관리자"])

with tab1:
    st.markdown("<h1 style='text-align:center;'>🏫 한일고 40기 신청 시스템 2.1</h1>", unsafe_allow_html=True)
    
    with st.form("apply_form"):
        sid = st.text_input("학번 (4자리)", placeholder="예: 1101")
        submit_btn = st.form_submit_button("정보 확인")

    if sid:
        try:
            # 마스터 시트 읽기
            master_df = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
            master_df.columns = master_df.columns.str.strip() # 제목 공백 제거
            master_df['학번'] = master_df['학번'].astype(str).str.strip()
            
            student_info = master_df[master_df['학번'] == sid.strip()]
            
            if not student_info.empty:
                name = student_info.iloc[0]['이름']
                # 열 이름이 '반' 또는 '학급'인 것을 찾음
                s_class = student_info.iloc[0].get('반', student_info.iloc[0].get('학급', "미지정"))
                # 열 이름이 '호실' 또는 '기숙사 호실'인 것을 찾음
                s_room = student_info.iloc[0].get('호실', student_info.iloc[0].get('기숙사 호실', "미지정"))
                
                st.success(f"✅ 확인 완료: **{s_class}반 {name} (호실: {s_room})**")
                
                with st.expander("📍 신청 내용 작성", expanded=True):
                    cat = st.radio("구분", ["귀성", "토요외출", "일요외출"], horizontal=True)
                    reason = st.text_input("사유 (5자 이상)")
                    final_submit = st.button("🚀 최종 제출")
                
                if final_submit and len(reason) >= 5:
                    # 데이터 저장 로직 (data, 이번주_명단, 통계_현황 탭 업데이트)
                    data_df = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                    new_row = pd.DataFrame([{
                        "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "학번": sid, "이름": name, "반": s_class, "호실": s_room,
                        "구분": cat, "사유": reason, "대상주말": target_weekend_str
                    }])
                    
                    # 3개 시트 동시 업데이트
                    updated_data = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                    conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_data)
                    conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=updated_data[updated_data['대상주말']==target_weekend_str])
                    
                    st.success("🎉 신청이 완료되었습니다!")
                    st.balloons()
            else:
                st.error(f"❌ '{sid}' 학번을 마스터 명단에서 찾을 수 없습니다. (현재 명단 수: {len(master_df)}명)")
        except Exception as e:
            st.error(f"오류 발생: {e}")

# 관리자 모드는 이전과 동일하게 유지...
# --- [TAB 2: 관리자 모드] ---
with tab2:
    st.subheader("👨‍🏫 학년부 관리 도구")
    admin_pw = st.text_input("관리자 비번", type="password")
    if admin_pw == "hanil40":
        try:
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
                
                csv = week_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 이번 주 명단 다운로드", csv, f"명단_{target_weekend_str}.csv")
        except Exception as e:
            st.error(f"관리자 데이터 로드 오류: {e}")
