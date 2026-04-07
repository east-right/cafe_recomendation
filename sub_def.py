import openai
import os
import json
from dotenv import load_dotenv
from string import Template
load_dotenv()

def _call_llm(system_prompt, user_prompt, model="gpt-5-mini"):

    api_key = os.getenv("openai_api_key")
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
    result = response.choices[0].message.content

    return result


def _generate_soar_rule(num, topic, property_val):
    top_num = num -1
    
    # desc 대신 topic과 property를 직접 사용하여 주석 생성
    top_tmpl = Template("""# $num차 심사 (S$num) - $topic/$property
sp {resolve*tie*S$num*judge
   (state <s> ^impasse <any-impasse> 
              ^superstate <s$top_num>
              ^item <o1> ^item <o2>
              ^top-state <ts>)""")

    middle_lines = []
    for i in range(top_num, 1, -1):
        middle_lines.append(f"   (<s{i}> ^superstate <s{i-1}>)")
    middle_str = "\n".join(middle_lines) if middle_lines else ""

    bottom_tmpl = Template("""   (<s1> ^superstate nil)

   (<o1> ^name recommend-cafe ^cafe-name <c1-name>)
   (<o2> ^name recommend-cafe ^cafe-name <c2-name> <> <c1-name>)
   (<ts> ^io.input-link <il>)
   (<il> ^cafe <c1> ^cafe <c2>)

   (<c1> ^name <c1-name> ^feature <f1>)
   (<f1> ^topic |$topic| ^property |$property|)
   (<c2> ^name <c2-name>)
   - { (<c2> ^feature <f2>) (<f2> ^topic |$topic| ^property |$property|) }
-->
   (<s1> ^operator <o1> > <o2>)
}""")

    top_str = top_tmpl.substitute(num=num, topic=topic, property=property_val, top_num=top_num)
    bottom_str = bottom_tmpl.substitute(topic=topic, property=property_val)

    return f"{top_str}\n{middle_str}\n{bottom_str}" if middle_str else f"{top_str}\n{bottom_str}"

# 2. ASK-LLM 생성 파트
def _generate_sos_rule(top_num):
    depth = top_num +1
    
    top_tmpl = Template("""# LLM 호출
sp {resolve*tie*S$depth*ask-llm
   # state 확인 밑 정리
   (state <s> ^impasse <any-impasse>
              ^superstate <s$top_num>
              ^item <o1> ^item <o2> 
              ^top-state <ts>)""")

    middle_lines = []
    for i in range(top_num, 1, -1):
        middle_lines.append(f"   (<s{i}> ^superstate <s{i-1}>)")
    middle_lines.append("   (<s1> ^superstate nil)")
    middle_str = "\n".join(middle_lines)

    bottom_tmpl = Template("""
   (<o1> ^cafe-name <c1-name>)
   (<o2> ^cafe-name { <c2-name> > <c1-name> }) 

   # 2. 1층 우편함 확인
   (<ts> ^io.output-link <ol>)
-->
   # 3. 파이썬으로 최종 SOS 발사
   (<ol> ^ask-llm <req>)
   (<req> ^cand1 <c1-name>
          ^cand2 <c2-name>
          ^stopped-depth $depth)
}""")

    top_str = top_tmpl.substitute(depth=depth, top_num=top_num)
    bottom_str = bottom_tmpl.substitute(depth=depth)

    return f"{top_str}\n{middle_str}\n{bottom_str}"


# 통합 빌더 함수 (LLM 디폴트 적용)
def _build_soar_agent(BASE_RULE,dynamic_rules=None):
    """
    베이스 룰 + 동적 룰 + (자동 계산된 깊이의) LLM SOS 룰을 하나로 합칩니다.
    """
    if dynamic_rules is None:
        dynamic_rules = []

    BASE_RULE_SPLIT = BASE_RULE.split('# LLM 호출')[0]    
    final_code = BASE_RULE_SPLIT + "\n"
    
    # 추가된 룰이 있다면 순회하며 생성 
    for rule in dynamic_rules:
        final_code += _generate_soar_rule(rule['num'], rule['topic'], rule['property']) + "\n\n"
             
    final_code += _generate_sos_rule(rule['num']) + "\n"
    
    return final_code

def _generate_elaborate_candidate_rule(topic, property_val, idx):
    tmpl = Template("""
sp {elaborate*candidate*$idx
   (state <s> ^io.input-link <il>)
   (<il> ^cafe <c>)
   (<c> ^name <c-name> ^feature <f> )
   (<f> ^topic |$topic| ^property |$property|)
-->
   (<s> ^candidate <c-name>)
}""")
    return tmpl.substitute(topic=topic, property=property_val, idx=idx)

# 1-5. (신규 추가) 진짜 오퍼레이터 단일 생성 룰
def _generate_universal_propose_rule():
    return """
# 수집한 후보들 +로 등록
sp {recommend*OPERATOR*propose
   (state <s> ^candidate <c-name>)
-->
   (<s> ^operator <o> +)
   (<o> ^name recommend-cafe ^cafe-name <c-name>)
}
"""

# 2. S1 Judge 룰 (가장 중요한 1순위 전용)
def _generate_s1_judge_rule(topic, property_val):
    tmpl = Template("""
# 1차 심사 (S1) - 기본 제안 & $topic/$property
sp {recommend*S1*judge
   (state <s> ^operator <o1> +
              ^operator <o2> +
              ^io.input-link <il>)
   (<o1> ^name recommend-cafe ^cafe-name <c1-name>)
   (<o2> ^name recommend-cafe ^cafe-name <c2-name> <> <c1-name>)
   (<il> ^cafe <c1> ^cafe <c2>)
   (<c1> ^name <c1-name> ^feature <f1>)
   (<f1> ^topic |$topic| ^property |$property|)
   (<c2> ^name <c2-name>)
   - { (<c2> ^feature <f2>) (<f2> ^topic |$topic| ^property |$property|) }
-->
   (<s> ^operator <o1> > <o2>)
}""")
    return tmpl.substitute(topic=topic, property=property_val)