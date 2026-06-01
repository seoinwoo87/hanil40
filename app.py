import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# ================= [학년부장님 맞춤형 자동 날짜 시스템] =================
today = datetime.now()
current_weekday = today.weekday() # 월:0, 화:1, 수:2, 목:3, 금:4, 토:5, 일:6

# 1. 학생용: 토/일요일 신청 차단 조건 (월~금만 오픈)
is_open = current_weekday < 5 

# 2. 학생용 다음 주 주말 날짜 자동 계산
days_until_next_sat = (5 - current_weekday) + 7
days_until_next_sun = (6 - current_weekday) + 7
target_saturday = today + timedelta(days=days_until_next_sat)
target_sunday = today + timedelta(days=days_until_next_sun)
student_week_title = f"{target_saturday.strftime('%m/%d')} ~ {target_sunday.strftime('%m/%d')}"
sat_str = target_saturday.strftime("%m월 %d일(토)")
sun_str = target_sunday.strftime("%m월 %d일(일)")

# 3. 선생님용 이번 주 처리 대상 주말 날짜 계산
days_until_this_sat = 5 - current_weekday
days_until_this_sun = 6 - current_weekday
this_saturday = today + timedelta(days=days_until_this_sat)
this_sunday = today + timedelta(days=days_until_this_sun)
teacher_week_title = f"{this_saturday.strftime('%m/%d')} ~ {this_sunday.strftime('%m/%d')}"
# =============================================================================

# 데이터 저장용 CSV 파일 설정
DATA_FILE = "weekend_requests.csv"

if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["조사주차", "신청시간", "반", "번호", "이름", "구분", "사유", "귀가/외출 일시"])
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# 웹페이지 기본 설정
st.set_page_config(page_title="학년 귀성/외출 관리 시스템", page_icon="🏫")
st.title("🏫 우리 학년 귀성·외출 신청 시스템")
st.markdown("---")

tab1, tab2 = st.tabs(["📋 학생 신청하기", "👨‍🏫 선생님 관리 모드"])

# ------------------ [📋 학생 신청 탭] ------------------
with tab1:
    if is_open:
        # 🌟 처음처럼 깔끔하게 헤더와 설명글로만 첫 화면 구성! 날짜만 제목에 자연스럽게 녹였습니다.
        st.header(f"주말 귀성 및 외출 신청 ({sat_str} ~ {sun_str})")
        st.caption("정확하게 입력 후 '신청하기' 버튼을 눌러주세요.")
        
        with st.form(key="request_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                class_num = st.selectbox("반", [f"{i}반" for i in range(1, 11)])
            with col2:
                student_num = st.number_input("번호", min_value=1, max_value=40, step=1)
            with col3:
                name = st.text_input("이름")
                
            # 🌟 '금요귀성'을 빼고 세 가지만 깔끔하게 배치했습니다.
            category = st.radio("구분", ["토요귀성", "외출(당일 복귀)", "잔류"])
            
            date_time = st.text_input("귀가/외출 일시 예시", placeholder=f"예시: {sat_str} 오전 10시 나감 / 저녁 6시 복귀")
            reason = st.text_area("사유 (외출 시 필수 입력)")
            
            submit_button = st.form_submit_button(label="🚀 신청하기")
            
            if submit_button:
                if not name:
                    st.error("이름을 입력해주세요!")
                else:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_data = pd.DataFrame([{
                        "조사주차": student_week_title,
                        "신청시간": current_time,
                        "반": class_num,
                        "번호": f"{student_num}번",
                        "이름": name,
                        "구분": category,
                        "사유": reason if reason else "없음",
                        "귀가/외출 일시": date_time
                    }])
                    
                    df_existing = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
                    df_updated = pd.concat([df_existing, new_data], ignore_index=True)
                    df_updated.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
                    
                    st.success(f"🎉 {class_num} {student_num}번 {name} 학생의 신청이 완료되었습니다!")
    else:
        # 주말 접속 시에도 큰 상자 없이 깔끔하게 텍스트로만 마감 안내
        st.header("주말 귀성 및 외출 신청")
        st.write("❌ **지금은 신청 기간이 아닙니다.**")
        st.caption("주말 귀성 및 외출 신청은 월요일부터 금요일까지만 가능합니다. 토/일요일은 시스템이 마감됩니다.")

# ------------------ [👨‍🏫 선생님 관리 탭] ------------------
with tab2:
    st.header("👨‍🏫 명단 확인 및 관리")
    password = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if password == "1234":
        st.success("인증되었습니다.")
        
        df_display = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
        
        all_weeks = df_display["조사주차"].unique().tolist() if not df_display.empty else []
        if teacher_week_title not in all_weeks:
            all_weeks.append(teacher_week_title)
            
        all_weeks.sort()
        default_idx = all_weeks.index(teacher_week_title)
        
        st.help(f"📅 **이번 주 처리(결재) 대상 주차:** `{teacher_week_title}` (지난주에 학생들이 신청한 내역입니다.)")
        
        selected_week = st.selectbox("조사 주차 선택", all_weeks, index=default_idx)
        
        df_week_filtered = df_display[df_display["조사주차"] == selected_week] if not df_display.empty else df_display
        
        filter_class = st.selectbox("반별 필터", ["전체보기"] + [f"{i}반" for i in range(1, 11)])
        if filter_class != "전체보기":
            df_filtered = df_week_filtered[df_week_filtered["반"] == filter_class]
        else:
            df_filtered = df_week_filtered
            
        st.subheader(f"📊 {selected_week} 주차 신청 현황 (총 {len(df_filtered)}명)")
        st.dataframe(df_filtered)
        
        st.markdown("---")
        csv_data = df_filtered.to_csv(index=False, encoding="utf-8-sig").encode('utf-8-sig')
        st.download_button(
            label="📥 선택한 주차 명단 엑셀(CSV) 다운로드",
            data=csv_data,
            file_name=f"귀성외출명단_{selected_week.replace(' / ', '_')}.csv",
            mime="text/csv"
        )
            
    elif password:
        st.error("비밀번호가 틀렸습니다.")
