import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# ==========================================
# 1. 필수 설정 (부장님 시트 정보로 수정)
# ==========================================
# [중요] SHEET_URL에 부장님의 구글 시트 주소를 넣으세요.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

st.set_page_config(page_title="한일고 40기 통합 관리시스템", page_icon="🏫", layout="centered")

# CSS 디자인
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #f0f2f6; border-radius: 10px 10px 0px 0px; font-weight: bold;
    }
    .stTabs [aria-selected="true"] { background-color: #002147; color: white; }
    .status-box { background-color: #002147; color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 날짜 계산 로직 (금주 월요일 08:00 기준)
# ==========================================
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

# 월요일 8시 전이면 이번 주말, 후면 다음 주말 타겟팅
if now < deadline:
    target_sat = deadline + timedelta(days=5)
else:
    target_sat = deadline + timedelta(days=12)

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# --- [상단 탭 분리] ---
tab1, tab2 = st.tabs(["📝 신청서 제출", "👨‍🏫 선생님 전용 관리자"])

# ==========================================
# 3. [TAB 1] 학생 신청 화면
# ==========================================
with tab1:
    st.markdown("<h1 style='text-align:center; color:#002147;'>🏫 한일고 40기 신청 시스템</h1>", unsafe_allow_html=True)
    st.markdown(f'<div class="status-box"><b>현재 신청 주말: {target_weekend_str}</b></div>', unsafe_allow_html=True)

    # 1단계: 학번 인증
    with st.form("auth_form"):
        input_sid = st.text_input("학번 4자리를 입력하세요", placeholder="예: 1101")
        auth_btn = st.form_submit_button("학생 정보 확인")

    if input_sid:
        try:
            # 마스터 데이터 로드 및 전처리 (학번 매칭 강화)
            master_df = conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0)
            master_df.columns = master_df.columns.str.strip() # 헤더 공백 제거
            
            # 시트의 학번 데이터를 문자로 변환 후 소수점(.0) 제거 및 공백 제거
            master_df['학번'] = master_df['학번'].astype(str).str.replace(".0", "", regex=False).str.strip()
            search_sid = input_sid.strip()
            
            student_info = master_df[master_df['학번'] == search_sid]

            if not student_info.empty:
                # 학생 정보 추출
                s_name = student_info.iloc[0]['이름']
                s_class = student_info.iloc[0].get('반', "미지정")
                s_room = student_info.iloc[0].get('호실', student_info.iloc[0].get('기숙사 호실', "미지정"))
                
                st.success(f"✅ 확인되었습니다: **{s_class}반 {s_name}** (기숙사: {s_room})")

                # 2단계: 상세 신청 내역
                with st.expander("📍 신청 내용 작성", expanded=True):
                    cat = st.radio("구분", ["귀성", "토요외출", "일요외출"], horizontal=True)
                    time_opt = ["토요일 오후", "일요일 오전", "일요일 오후", "기타(사유란 기재)"]
                    stime = st.selectbox("예정 시간", time_opt)
                    reason = st.text_input("사유 및 목적지 (5자 이상)", placeholder="구체적으로 입력해 주세요.")
                    
                    final_submit = st.button("🚀 최종 신청서 제출")

                if final_submit:
                    if len(reason) < 5:
                        st.error("사유를 5자 이상 상세히 입력해 주세요.")
                    else:
                        # 데이터 업데이트 시작
                        full_data = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                        
                        # 중복 신청 체크
                        if not full_data[(full_data['학번'].astype(str) == search_sid) & (full_data['대상주말'] == target_weekend_str)].empty:
                            st.warning(f"⚠️ {s_name} 학생은 이미 이번 주말({target_weekend_str}) 신청 내역이 있습니다.")
                        else:
                            new_row = pd.DataFrame([{
                                "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "학번": search_sid, "이름": s_name, "반": s_class, "호실": s_room,
                                "구분": cat, "귀가/외출 일시": stime, "사유": reason, "대상주말": target_weekend_str
                            }])
                            
                            # (1) data 탭 업데이트 (전체 누적)
                            updated_all = pd.concat([full_data, new_row], ignore_index=True).fillna("").astype(str)
                            conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_data)
                            
                            # (2) 이번주_명단 탭 업데이트 (해당 주말만 필터링)
                            this_week_data = updated_all[updated_all['대상주말'] == target_weekend_str]
                            conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=this_week_data)
                            
                            # (3) 통계_현황 탭 업데이트
                            stat_df = this_week_data.groupby('구분').size().reset_index(name='인원수')
                            conn.update(spreadsheet=SHEET_URL, worksheet="통계_현황", data=stat_df)
                            
                            st.success("🎉 신청이 완료되었습니다! 안전하게 다녀오세요.")
                            st.balloons()
            else:
                st.error(f"❌ '{search_sid}' 학번을 마스터 명단에서 찾을 수 없습니다.")
                st.info("명단에 본인 학번이 없다면 학년부실로 문의하세요.")

        except Exception as e:
            st.error(f"연동 오류 발생: {e}")

# ==========================================
# 4. [TAB 2] 선생님 관리자 화면
# ==========================================
with tab2:
    st.markdown("<h2 style='text-align:center;'>👨‍🏫 학년부 관리 포털</h2>", unsafe_allow_html=True)
    
    admin_pw = st.text_input("관리자 비밀번호", type="password")
    
    if admin_pw == "hanil40":
        try:
            # 이번 주 명단 시트 읽기
            view_df = conn.read(spreadsheet=SHEET_URL, worksheet="이번주_명단", ttl=0).dropna(how="all")
            
            if not view_df.empty:
                # 간단 통계
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("총 인원", f"{len(view_df)}명")
                c2.metric("귀성", f"{len(view_df[view_df['구분']=='귀성'])}명")
                c3.metric("토요외출", f"{len(view_df[view_df['구분']=='토요외출'])}명")
                c4.metric("일요외출", f"{len(view_df[view_df['구분']=='일요외출'])}명")
                
                # 차트 시각화
                fig = px.pie(view_df, names='구분', title=f"{target_weekend_str} 신청 비율")
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                # 검색 기능
                q = st.text_input("🔍 학생 검색 (이름, 반, 호실 등으로 검색)")
                if q:
                    view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(q)).any(axis=1)]
                
                st.write(f"📋 **상세 명단 (검색 결과: {len(view_df)}건)**")
                st.dataframe(view_df, use_container_width=True)
                
                # 엑셀/CSV 다운로드
                csv_data = view_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 이번 주 명단 다운로드(CSV)", csv_data, f"40기_명단_{target_weekend_str}.csv")
            else:
                st.info("이번 주 신청 내역이 아직 없습니다.")
        except:
            st.error("관리자 데이터를 불러오는 중 오류가 발생했습니다. 시트의 탭 이름을 확인해 주세요.")
