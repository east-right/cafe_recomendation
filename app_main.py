import sys
import subprocess

def main():
    print("🚀 [Soar + LangGraph] 카페 추천 시스템 Streamlit UI를 시작합니다...")
    print("종료하려면 터미널에서 Ctrl+C를 누르세요.\n")
    
    try:
        # 파이썬 환경에 설치된 streamlit 모듈을 호출하여 app.py를 실행합니다.
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n시스템을 종료합니다. 수고하셨습니다!")
    except Exception as e:
        print(f"\n❌ 실행 중 에러가 발생했습니다: {e}\n")

if __name__ == "__main__":
    main()