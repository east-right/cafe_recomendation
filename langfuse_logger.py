# langfuse_logger.py
import os
from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler

# 1. .env 파일의 환경변수들을 시스템으로 불러옵니다.
load_dotenv()

# 2. 전역 싱글톤 핸들러 생성
# (.env에서 불러온 LANGFUSE_* 키들을 알아서 가져다 씁니다)
_lf_handler = CallbackHandler()

# 3. main.py에서 가져다 쓸 config 딕셔너리
lf_config = {"callbacks": [_lf_handler]}

# 4. 시스템 종료 시 호출할 flush 함수
def flush_logs():
    print("📦 Langfuse 서버로 남은 로그를 전송합니다...")
    _lf_handler.flush()
    print("✅ 로그 전송 완료!")