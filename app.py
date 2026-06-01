import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 필수 설정
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/부장님_시트_ID/edit#gid=0"

st.set_page_config(page_title="한일고 40기 귀성외출 신청", page_icon="🏫", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght=500;700;900&display=swap');
    
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
    .banner-sub { font-size: 1.6rem; font-weight: 900; color: #cbd5e1; margin-bottom: 12px; letter-spacing: 1px; }
    .banner-main { font-size: 2.5rem; font-weight: 900; color: #deff9a; }
    
    .section-header {
        background-color: #e2e8f0;
        border-left: 8px solid #0f172a;
        padding: 12px 18px;
        font-weight: 900;
        font-size: 1.2rem;
        margin: 30px 0 15px 0;
        border-radius: 0 10px 10px 0;
    }

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

# ==========================================
# 한일고 40기 맞춤형 날짜 이원화 계산 시스템
# ==========================================
today = datetime.now()
current_weekday = today.weekday() # 월:0, 화:1, 수:2, 목:3, 금:4, 토:5, 일:6

is_open = current_weekday < 5 # 월~금요일만 오픈

# [학생용] 다음 주 주말 날짜 계산
days_to_next_sat = (5 - current_weekday) + 7
student_sat = today + timedelta(days=days_to_next_sat)
student_sun = student_sat + timedelta(days=1)
student_weekend_str = f"{student_sat.strftime('%m/%d')}(토) ~ {student_sun.strftime('%m/%d')}(일)"

# [교사용] 이번 주 처리(결재) 대상 주말 날짜 계산 (지난주 신청분)
days_to_this_sat = 5 - current_weekday
teacher_sat = today + timedelta(days=days_to_this_sat)
teacher_sun = teacher_sat + timedelta(days=1)
teacher_weekend_str = f"{teacher_sat.strftime('%m/%d')}(토) ~ {teacher_sun.strftime('%m/%d')}(일)"

# --- 상단 배너 ---
st.markdown(f"""
    <div class="main-banner">
        <div class="banner-sub">한일고 40기 귀성외출 신청</div>
        <div class="banner-main">📅 {student_weekend_str}</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 학생 신청", "👨‍🏫 교사용 관리"])

# ==========================================
# [TAB 1] 학생 신청
# ==========================================
with tab1:
    st.markdown('<p class="warning-text">⚠️ 주의: 주말 귀성 및 외출 신청은 월요일부터 금요일까지만 가능합니다. 토요일 00시 이후에는 시스템이 자동으로 마감됩니다.</p>', unsafe_allow_html=True)
    
    if is_open:
        st.markdown('<div class="section-header">본인 확인 및 내용 작성</div>', unsafe_allow_html=True)
        
        input_sid = st.text_input("학번 4자리 (예: 1101)")
        cat = st.radio("구분", ["토요귀성", "토요 외출", "일요 외출", "기타"], horizontal=True)
        
        detailed_time = ""
        if cat == "기타":
            detailed_time = st.text_input("📍 상세 일정을 직접 입력하세요 (예: 금요일 조기 귀성 등)")
        
        base_reason = st.text_input("구체적 사유 (목적지 포함 5자 이상)")

        st.markdown("---")
        
        confirm_check = st.checkbox("위 신청 내용이 본인의 것이며 사실임을 확인합니다.")
        submit_btn = st.button("🚀 신청서 최종 제출하기", disabled=not confirm_check)

        if submit_btn:
            if not input_sid or len(base_reason) < 5:
                st.error("학번 and 사유를 정확히 입력해주세요.")
            elif cat == "기타" and not detailed_time:
                st.error("기타 선택 시 상세 일정을 필수 입력해야 합니다.")
            else:
                try:
                    master_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="99_학생_마스터", ttl=0))
                    student = master_df[master_df['학번'] == input_sid.strip()]

                    if not student.empty:
                        s_name = student.iloc[0]['이름']
                        s_room = student.iloc[0].get('호실', student.iloc[0].get('기숙사 호실', '-'))
                        s_class = student.iloc[0].get('반', "-")
                        
                        data_df = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0).dropna(how="all"))
                        
                        if not data_df[(data_df['학번'] == input_sid.strip()) & (data_df['대상주말'] == student_weekend_str)].empty:
                            st.warning(f"⚠️ {s_name} 학생은 이미 이번 기간 신청 내역이 존재합니다.")
                        else:
                            final_reason = f"[{detailed_time}] {base_reason}" if cat == "기타" else base_reason
                            
                            new_row = pd.DataFrame([{
                                "신청시간": datetime.now().strftime("%m-%d %H:%M"),
                                "학번": input_sid.strip(), 
                                "이름": s_name, 
                                "반": s_class, 
                                "호실": s_room, 
                                "구분": cat, 
                                "귀가/외출 일시": detailed_time if cat == "기타" else cat, 
                                "사유": final_reason, 
                                "대상주말": student_weekend_str
                            }])
                            
                            updated_all = pd.concat([data_df, new_row], ignore_index=True).astype(str)
                            conn.update(spreadsheet=SHEET_URL, worksheet="data", data=updated_all)
                            conn.update(spreadsheet=SHEET_URL, worksheet="이번주_명단", data=updated_all[updated_all['대상주말'] == student_weekend_str])
                            st.balloons()
                            st.success(f"✅ [{s_room} {s_name}] 학생, 신청이 완료되었습니다! (호실 자동 매핑 완료)")
                    else:
                        st.error("❌ 등록되지 않은 학번입니다. 본인의 학번을 확인하세요.")
                except Exception as e:
                    st.error(f"오류: {e}")
    else:
        st.markdown('<div class="section-header">📋 신청 마감 안내</div>', unsafe_allow_html=True)
        st.error("❌ **지금은 신청 기간이 아닙니다.**")
        st.info("주말 귀성 및 외출 신청은 평일(월~금)에만 가능합니다. 토/일요일은 다음 주 조사를 위해 시스템이 마감됩니다.")

# ==========================================
# [TAB 2] 교사용 관리
# ==========================================
with tab2:
    admin_pw = st.text_input("교사용 비밀번호", type="password")
    if admin_pw == "hanil40":
        try:
            full_data = clean_data(conn.read(spreadsheet=SHEET_URL, worksheet="data", ttl=0))
            
            st.markdown(f"### 🔄 이번 주 실시간 신청 현황 및 통계 (신청 기간: {student_weekend_str})")
            rt_df = full_data[full_data['대상주말'] == student_weekend_str]
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("총 신청", f"{len(rt_df)}명")
            c2.metric("토요귀성", f"{len(rt_df[rt_df['구분']=='토요귀성'])}명")
            c3.metric("토요 외출", f"{len(rt_df[rt_df['구분']=='토요 외출'])}명")
            c4.metric("일요 외출", f"{len(rt_df[rt_df['구분']=='일요 외출'])}명")
            c5.metric("기타", f"{len(rt_df[rt_df['구분']=='기타'])}명")
            
            st.dataframe(rt_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
            
            # 🌟 [수정] 부장님 요청대로 앞의 긴 수식어 지우고 깔끔하게 날짜만 남김
            st.markdown("---")
            st.markdown(f"### 📥 지난주 신청 내역 ({teacher_weekend_str})")
            lw_df = full_data[full_data['대상주말'] == teacher_weekend_str]
            
            if not lw_df.empty:
                def make_stat(df, idx):
                    if df.empty: return pd.DataFrame()
                    s = df.groupby([idx, '구분']).size().unstack(fill_value=0)
                    for c in ["토요귀성", "토요 외출", "일요 외출", "기타"]:
                        if c not in s.columns: s[c] = 0
                    s['합계'] = s.sum(axis=1)
                    return s[["토요귀성", "토요 외출", "일요 외출", "기타", "합계"]]

                conf = {
                    "토요귀성": st.column_config.NumberColumn("토요귀성", format="%d", width="small"),
                    "토요 외출": st.column_config.NumberColumn("토요 외출", format="%d", width="small"),
                    "일요 외출": st.column_config.NumberColumn("일요 외출", format="%d", width="small"),
                    "기타": st.column_config.NumberColumn("기타", format="%d", width="small"),
                    "합계": st.column_config.NumberColumn("합계", format="%d", width="small"),
                }

                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown('##### 🏫 학급별 통계 (결재 대상)')
                    class_stat = make_stat(lw_df, '반')
                    # 🌟 [수정] 표 내용 전체 가운데 정렬 적용 (.style.set_properties)
                    st.dataframe(class_stat.style.set_properties(**{'text-align': 'center'}), column_config=conf)
                    
                with col_right:
                    st.markdown('##### 🏢 호실별 통계 (결재 대상)')
                    room_stat = make_stat(lw_df, '호실')
                    # 🌟 [수정] 표 내용 전체 가운데 정렬 적용 (.style.set_properties)
                    st.dataframe(room_stat.style.set_properties(**{'text-align': 'center'}), column_config=conf)

                st.markdown('##### 📋 지난주 최종 신청 명단 표')
                st.dataframe(lw_df.sort_values(['반', '학번']), use_container_width=True, hide_index=True)
                
                csv = lw_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📂 지난주 결재 대상 명단 다운로드 (CSV)", csv, f"40기_결재명단_{teacher_weekend_str}.csv")
            else:
                st.write("해당 기간에 수집된 결재 대상 데이터가 없습니다.")

        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
