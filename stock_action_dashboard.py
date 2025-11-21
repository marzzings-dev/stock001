# -*- coding: utf-8 -*-
# 이 코드는 Streamlit 기반입니다. 실행 환경에서 streamlit 설치 필요: pip install streamlit
import pandas as pd
import altair as alt
from datetime import datetime
from email.mime.text import MIMEText
import smtplib

try:
    import streamlit as st
except ImportError:
    raise ImportError("이 코드는 Streamlit 환경에서 실행되어야 합니다. 'streamlit' 모듈이 설치되어 있는지 확인하세요.")

# 데이터 불러오기
@st.cache_data
def load_data():
    df = pd.read_csv("quantityavailable_2028-08-10.csv")
    df['입고일'] = pd.to_datetime(df['입고일'], errors='coerce')
    return df

df = load_data()
today = pd.to_datetime("2025-08-22")

# 파생 컬럼 생성
with st.spinner("데이터 계산 중..."):
    df['가용기간(일)'] = (today - df['입고일']).dt.days
    df['재고회전율'] = df['판매수량_직전3개월'] / (df['현재고수량'] + 1)

    df['유형'] = df['재고회전율'].apply(lambda x: '발주 필요' if x > (3/0.5) else None)
    df.loc[df['가용기간(일)'] >= 180, '유형'] = '반송 검토'
    df.loc[(df['가용기간(일)'] >= 30) & (df['유형'].isnull()), '유형'] = '프로모션 제안'

# MD 선택 필터
mds = df['MD'].dropna().unique().tolist()
selected_md = st.sidebar.selectbox("MD 선택", mds)
df_md = df[(df['MD'] == selected_md) & (df['유형'].notnull())]

st.title(f"📦 {selected_md} 재고 관리 대시보드")
st.caption("※ 유형: 발주 필요(재고회전율 낮음) / 프로모션 제안(1개월↑) / 반송 검토(6개월↑)")

# KPI 요약
col1, col2, col3 = st.columns(3)
col1.metric("총 대상 SKU 수", len(df_md))
col2.metric("평균 재고회전율", f"{df_md['재고회전율'].mean():.2f}")
col3.metric("평균 가용기간(일)", f"{df_md['가용기간(일)'].mean():.0f}일")

# 유형별 탭 구성
labels = ["발주 필요", "프로모션 제안", "반송 검토"]
tabs = st.tabs(labels)

for label, tab in zip(labels, tabs):
    with tab:
        subset = df_md[df_md['유형'] == label][['브랜드', '상품명', 'SKU', 'reference_no', '현재고수량']]
        st.subheader(f"📌 {label} 대상 SKU")
        st.dataframe(subset, use_container_width=True)

        # 이메일 내용 생성
        if not subset.empty:
            st.markdown("#### 이메일 미리보기")
            html_table = subset.to_html(index=False, justify='center')
            body = f"<p>{selected_md}님의 {label} 대상 재고 목록입니다.</p>" + html_table
            st.components.v1.html(body, height=300, scrolling=True)

            # 메일 발송 함수 정의
            def send_email(html_content, label_type):
                msg = MIMEText(html_content, 'html')
                msg['Subject'] = f"[{selected_md}] {label_type} 대상 재고 자동 알림"
                msg['From'] = 'your_email@example.com'
                msg['To'] = 'recipient@example.com'
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login('your_email@example.com', 'your_app_password')
                    server.send_message(msg)

            # 발송 버튼
            if st.button(f"📧 {label} 대상 메일 발송하기"):
                send_email(body, label)
                st.success("메일이 발송되었습니다.")
