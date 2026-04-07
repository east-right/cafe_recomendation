import streamlit as st
from flow import graph_flow
from langfuse_logger import lf_config, flush_logs

# 1. 페이지 설정
st.set_page_config(page_title="카페 추천 시스템", page_icon="☕", layout="centered")

st.title("🚀 Soar + LangGraph 카페 추천")
st.caption("찾고 싶은 카페 키워드를 입력하시면 맞춤형 카페를 추천해 드립니다.")

# 2. 세션 상태(Session State) 초기화
# LangGraph 앱을 한 번만 컴파일해서 세션에 저장해 둡니다.
if "app" not in st.session_state:
    st.session_state.app = graph_flow()

# 대화 기록을 저장할 리스트 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. 사이드바 - 로그 정리 및 대화 초기화 버튼 (터미널의 'quit' 역할 대체)
with st.sidebar:
    st.header("설정")
    if st.button("대화 초기화 및 로그 전송 🧹"):
        flush_logs()  # 🚨 기존 main.py의 종료 직전 로그 털어내기 기능
        st.session_state.messages = []
        st.rerun()

# 4. 기존 대화 기록 화면에 렌더링
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. 사용자 입력 처리
if user_query := st.chat_input("💬 찾고 싶은 카페 키워드를 입력하세요..."):
    # 사용자의 입력을 화면에 표시하고 기록에 추가
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    # AI(시스템) 응답 처리
    with st.chat_message("assistant"):
        with st.spinner("조건에 맞는 카페를 찾고 있습니다... ☕"):
            try:
                # 초기 상태 설정 (main.py와 동일)
                initial_state = {
                    "user_query": user_query,
                    "intent_dictionary": {} 
                }
                
                # 🚨 LangGraph invoke 실행
                result = st.session_state.app.invoke(
                    initial_state,
                    config=lf_config
                )
                
                # 결과 추출
                final_output = result.get("cafe_orDepth", "결과를 찾지 못했습니다.")
                
                # 화면에 결과 출력 및 기록에 추가
                st.markdown(final_output)
                st.session_state.messages.append({"role": "assistant", "content": final_output})
                
            except Exception as e:
                # 에러 발생 시 처리
                error_msg = f"❌ 실행 중 에러가 발생했습니다: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})