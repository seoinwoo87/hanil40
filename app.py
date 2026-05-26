import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px  # 그래프를 위한 라이브러리

# [필수] 구글 시트 주소 (data 탭 주소)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iKcWJJTC_M0CHYdHuRhreljlepWymPY6LLUX7N2sXug/edit?gid=766878989#gid=766878989"

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="한일고 40기 신청 시스템", page_icon="🏫", layout="centered")

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #f0f2f6; border-radius: 10px 10px 0px 0px; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #002147; color: white; }
    .main-title { text-align: center; color: #002147; font-size: 2.2em; font-weight: 800; padding: 15px; }
    .status-box { background: linear-gradient(135deg, #002147 0%, #003366 100%); color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .closed-box { background-color: #ffebee; color: #d32f2f; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; border: 2px solid #d32f2f; }
    </style>
    """, unsafe_allow_html=True)

# 2. 날짜 및 마감 로직
now = datetime.now()
this_monday = now - timedelta(days=now.weekday())
deadline = this_monday.replace(hour=8, minute=0, second=0, microsecond=0)

# 현재 시간이 마감 전이면 이번 주말, 마감 후면 다음 주말 타겟팅
if now < deadline:
    target_sat = deadline + timedelta(days=5) 
    is_open = True
else:
    target_sat = deadline + timedelta(days=12)
    # 월요일 8시 이후부터는 다음 신청을 위해 잠시 열어두되, 
    # 학교 정책에 따라 'is_open' 로직을 더 정교화할 수 있습니다.
    is_open = True 

target_sun = target_sat + timedelta(days=1)
target_weekend_str = f"{target_sat.strftime('%m/%d')}(토) ~ {target_sun.strftime('%m/%d')}(일)"

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

tab1, tab2 = st.tabs(["📝 신청서 제출", "👨‍🏫 관리자 모드"])

# --- [TAB 1: 신청 화면] ---
with tab1:
    st.markdown('<h1 class="main-title">🏫 한일고 40기 신청 시스템</h1>', unsafe_allow_html=True)
    
    # 마감 상태 표시
    if is_open:
        st.markdown(f'<div class="status-box"><p style="margin:0;">현재 신청 중인 주말</p><p style="font-size:1.6em; margin:5px 0;"><b>{target_weekend_str}</b></p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="closed-box">⚠️ 이번 주 신청이 마감되었습니다.<br>추가 신청은 학년부실로 문의하세요.</div>', unsafe_allow_html=True)

    with st.form("apply_form"):
        st.subheader("👤 학생 정보")
        c1, c2 = st.columns(2)
        sid = c1.text_input("학번 (4자리)", placeholder="예: 1101")
        sname = c2.text_input("성명", placeholder="실명 입력")
        
        st.markdown("---")
        st.subheader("📍 신청 내용")
        cat = st.radio("구분", ["귀성", "토요외출", "일요외출"], horizontal=True)
        
        c3, c4 = st.columns(2)
        time_opt = ["토요일 오후", "일요일 오전", "일요일 오후", "기타"]
        stime = c3.selectbox("예정 시간", time_opt)
        final_time = stime if stime != "기타" else st.text_input("상세 시간 입력")
            
        reason = c4.text_input("사유 및 목적지 (필수)", placeholder="5자 이상 구체적으로 작성")
        confirm = st.checkbox("본인 신청임을 확인합니다.")
        
        submit_btn = st.form_submit_button("🚀 신청서 제출하기", disabled=not is_open)

    if submit_btn:
        if not (sid.isdigit() and len(sid) == 4): st.error("학번 4자리를 정확히 입력하세요.")
        elif not sname: st.error("이름을 입력하세요.")
        elif not reason or len(reason) < 5: st.error("사유를 5자 이상 적어주세요.")
        elif not confirm: st.warning("확인 체크박스를 선택하세요.")
        else:
            try:
                # 데이터 읽기 및 중복 체크
                df = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
                
                # 중복 신청 확인 (동일 주말 + 동일 학번)
                duplicate = df[(df["학번"] == sid) & (df["대상주말"] == target_weekend_str)]
                
                if not duplicate.empty:
                    st.error(f"🛑 {sid} 학번은 이미 {target_weekend_str} 신청 기록이 있습니다. 수정을 원하시면 선생님께 말씀드리세요.")
                else:
                    new_row = pd.DataFrame([{
                        "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "학번": sid, "이름": sname, "구분": cat, 
                        "귀가/외출 일시": final_time, "사유": reason, "대상주말": target_weekend_str
                    }])
                    updated_df = pd.concat([df, new_row], ignore_index=True).fillna("").astype(str)
                    conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_df)
                    st.success("🎉 신청이 완료되었습니다!")
                    st.balloons()
            except Exception as e:
                st.error(f"저장 오류: {e}")

# --- [TAB 2: 관리자 모드] ---
with tab2:
    st.markdown("<h2 style='text-align:center;'>👨‍🏫 학년부 관리 시스템</h2>", unsafe_allow_html=True)
    pw = st.text_input("관리자 비밀번호", type="password")
    
    if pw == "hanil40":
        try:
            full_df = conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all")
            this_week_df = full_df[full_df["대상주말"] == target_weekend_str]
            
            # --- 상단 통계 ---
            st.markdown(f"#### 📊 {target_weekend_str} 현황")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("총 신청", f"{len(this_week_df)}건")
            m2.metric("귀성", f"{len(this_week_df[this_week_df['구분']=='귀성'])}건")
            m3.metric("토요외출", f"{len(this_week_df[this_week_df['구분']=='토요외출'])}건")
            m4.metric("일요외출", f"{len(this_week_df[this_week_df['구분']=='일요외출'])}건")
            
            # --- 그래프 시각화 ---
            if not this_week_df.empty:
                fig = px.pie(this_week_df, names='구분', title='신청 구분 비율', color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # --- 검색 및 명단 ---
            search = st.text_input("🔍 학생 검색 (학번 또는 이름 입력)", "")
            display_df = this_week_df.sort_index(ascending=False)
            
            if search:
                display_df = display_df[display_df["학번"].str.contains(search) | display_df["이름"].str.contains(search)]
            
            st.write(f"📂 **검색 결과: {len(display_df)}건**")
            st.dataframe(display_df, use_container_width=True)
            
            csv = display_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 명단 다운로드(CSV)", data=csv, file_name=f"hanil40_{target_weekend_str}.csv")

        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
