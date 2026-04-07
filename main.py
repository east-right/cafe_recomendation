# main.py
from flow import graph_flow
from langfuse_logger import lf_config, flush_logs

def main():
    print("🚀 [Soar + LangGraph] 카페 추천 시스템 MVP 시작!")
    print("종료하려면 'q', 'quit', 'exit' 중 하나를 입력하세요.\n")
    
    app = graph_flow()
    
    while True:
        user_input = input("💬 찾고 싶은 카페 키워드를 입력하세요: ").strip()
        
        # 종료 조건
        if user_input.lower() in ['q', 'quit', 'exit']:
            flush_logs()  # 🚨 종료 직전에 한 줄 추가 (로그 털어내기)
            print("시스템을 종료합니다. 수고하셨습니다!")
            break
            
        if not user_input:
            continue
            
        initial_state = {
            "user_query": user_input,
            "intent_dictionary": {} 
        }
        
        try:
            # 🚨 invoke 실행 시 config 매개변수로 lf_config만 쏙 넣어줍니다!
            result = app.invoke(
                initial_state,
                config=lf_config
            )
            
            final_output = result.get("cafe_orDepth", "결과를 찾지 못했습니다.")
            print(f"\n☕ 추천 결과: {final_output}\n")
            print("-" * 50)
            
        except Exception as e:
            print(f"\n❌ 실행 중 에러가 발생했습니다: {e}\n")

if __name__ == "__main__":
    main()