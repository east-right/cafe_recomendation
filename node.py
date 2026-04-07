
import os
import sys
import json
import pandas as pd
from core.state import GraphState 
from core.Soar.out import Python_sml_ClientInterface as sml
from llm_prompt import (
    impasse_system_prompt,
    impasse_user_prompt,
    system_prompt_initial_rule,
    generate_initial_rules_LLM,
    in_keyword_system_prompt,
    new_kewyword_system_prompt,
    _make_keyword_user_prompt,
)

from sub_def import (
    _call_llm,
    _build_soar_agent,
    _generate_elaborate_candidate_rule,
    _generate_universal_propose_rule,
    _generate_s1_judge_rule,
    _generate_sos_rule
)

def start_node(state: GraphState):
    data = pd.read_csv("./data/final_signature_df.csv", encoding = 'cp949')
    data = data.iloc[:,1:]
    data = data.dropna().reset_index(drop=True)
    data = data.rename(columns = {'topic_75': "topic", "cleaned_property": "property"})

    cafe_candidates = {}
    for store_name, group in data.groupby('store'):
        renamed_group = group[['topic', 'property']]
        features_list = renamed_group.to_dict('records')
        cafe_candidates[store_name] = {"features": features_list}

    dup_data = data[['topic','property']].drop_duplicates().reset_index(drop=True)
    dup_data_json = dup_data.to_dict('records')
    return {"cafe_candidates": cafe_candidates, "dup_data" : dup_data_json}

def select_keyword(state: GraphState):
  from pathlib import Path
  
  user_query = state.get('user_query', None)

  folder_path = "./soar_rule"
  soar_files = [file.stem for file in Path(folder_path).glob("*.soar")]
  soar_files = [i for i in soar_files if i != 'base']
  print("soar_files:", soar_files)

  user_prompt = _make_keyword_user_prompt(soar_files, user_query)
  result = _call_llm(in_keyword_system_prompt, user_prompt)
  print("soar_files_result:", result)
  if result == 'False':
      result = _call_llm(new_kewyword_system_prompt, user_query)
      
  return {"keyword":result}

def loadRule(state: GraphState):
    keyword = state.get('keyword', None)
    file_path = f"./soar_rule/{keyword}.soar"

    # 파일이 존재하는지 확인
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            # ⭕️ 성공 시: rule 내용과 함께 분기용 status 반환
            return {"rule": f.read()} 
            
    else:
        # ⭕️ 실패 시: 단순 문자열이 아닌 딕셔너리 형태로 반환!
        return {"rule": "no_rule_keyword"}


def recommendation_soar(state: GraphState):
    
    rule = state.get('rule', None)
    cafe_candidates = state.get('cafe_candidates', None)
    
    # 누적된 결과를 담을 리스트 (처음엔 비어있거나 이전 값이 담겨있음)
    results = state.get('results', []) 

    # 1. 커널 및 에이전트 생성
    kernel = sml.Kernel.CreateKernelInNewThread()
    agent = kernel.CreateAgent("CafeAgent")
    input_link = agent.GetInputLink()

    # 2. 데이터 주입
    for cafe_name, cafe_data in cafe_candidates.items():
        cafe_id = agent.CreateIdWME(input_link, "cafe")
        agent.CreateStringWME(cafe_id, "name", cafe_name)
        
        for feature in cafe_data["features"]:
            feat_id = agent.CreateIdWME(cafe_id, "feature")
            agent.CreateStringWME(feat_id, "topic", feature["topic"])
            agent.CreateStringWME(feat_id, "property", feature["property"])

    agent.Commit()
    
    # 3. 룰 적용 및 실행
    agent.ExecuteCommandLine(rule)
    agent.RunSelfTilOutput()
    
    # 4. 결과 확인
    output_link = agent.GetOutputLink()
    num_commands = agent.GetNumberCommands()
    
    tied_cafes = set()
    stopped_depth = None
    is_impasse = False

    for i in range(num_commands):
        command = agent.GetCommand(i)
        if command.GetCommandName() == "ask-llm":
            is_impasse = True
            cand1 = command.GetParameterValue("cand1")
            cand2 = command.GetParameterValue("cand2")
            depth = command.GetParameterValue("stopped-depth")
            
            if cand1: tied_cafes.add(cand1)
            if cand2: tied_cafes.add(cand2)
            if depth: stopped_depth = depth

    if is_impasse:
        final_state_update = {"status": "impasse", "cafe_orDepth": (list(tied_cafes), stopped_depth)}
    else:
        if output_link is not None:
            # 정상적으로 결과가 나왔을 때
            result = output_link.GetParameterValue("final-recommendation")
            if result: # 결과값이 비어있지 않은지 한번 더 확인
                results.append(result)
        else:
            print(" [ERROR] Soar 추천 로직 에러뜸 확인")
            
        final_state_update = {"status": "Success", "results": results, "cafe_orDepth": results}

    kernel.Shutdown()
    print("final_state_update: ", final_state_update)
    # 6. 랭그래프 상태 업데이트 반환
    return final_state_update


def view_intent_dictionary(state: GraphState):
    # 1. 저장된 JSON 파일 불러오기
    file_path = "./soar_rule/intent_dictionary.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            intent_dictionary = json.load(f)
    else:
        intent_dictionary = {}
    
    keyword = state.get('keyword', None)
    cafe_orDepth = state.get('cafe_orDepth', None)
    final_candidates = cafe_orDepth[0]
    cafe_candidates = state.get('cafe_candidates', None)

    # 키워드 데이터 안전하게 가져오기 (없으면 빈 리스트)
    intent_list = intent_dictionary.get(keyword, [])
    intent_set = set((item['topic'], item['property']) for item in intent_list)

    # 2. 특징(feature) 추출
    extracted_features = set()
    for name in final_candidates:
        if name in cafe_candidates:  
            # 이전 디버깅 내용 반영: 바로 리스트를 순회
            for feature in cafe_candidates[name]["features"]: 
                extracted_features.add((feature['topic'], feature['property']))

    # 3. 중복된(이미 적용된) 룰 제거
    filtered_features = extracted_features - intent_set

    # 4. JSON 포맷으로 복구
    llm_intent_dict = [{"topic": t, "property": p} for t, p in filtered_features]
    return{ "llm_intent_dict": llm_intent_dict, "intent_dictionary": intent_dictionary}


def ImpasseLLM(state: GraphState):

    keyword = state.get('keyword', None)
    llm_intent_dict = state.get('llm_intent_dict', None)

    system_prompt = impasse_system_prompt
    user_prompt = impasse_user_prompt(keyword, llm_intent_dict)
    result = _call_llm(system_prompt, user_prompt)
    if result.startswith("```json"):
        result = result[7:-3].strip()
    elif result.startswith("```"):
        result = result[3:-3].strip()
    
    new_rule_topic = json.loads(result)    
    return {'llm_output': new_rule_topic}


def update_rule(state: GraphState):
    rule = state.get('rule', None)
    # 초기값이 없을 경우를 대비해 or {} 추가
    intent_dictionary = state.get('intent_dictionary') or {}
    keyword = state.get('keyword', None)
    
    llm_output = state.get('llm_output', {})
    cafe_orDepth = state.get('cafe_orDepth', None)

    llm_result_dict = llm_output.get('selected_feature', {})
    new_rule_keyword = [{"num": int(cafe_orDepth[1]), "topic": llm_result_dict['topic'], "property": llm_result_dict['property']}]
    new_rule = _build_soar_agent(rule, new_rule_keyword)
    

    if keyword not in intent_dictionary:
        intent_dictionary[keyword] = []
    intent_dictionary[keyword].append(llm_result_dict)
    
    return {"rule": new_rule, "intent_dictionary": intent_dictionary}


def update_intent_dictionary(state: GraphState):
    save_dir = "./soar_rule"
    os.makedirs(save_dir, exist_ok=True) # 폴더가 없으면 생성

    
    keyword = state.get('keyword', None)
    new_rule = state.get('rule', None)
    intent_dictionary = state.get('intent_dictionary', None)

    # 1. 새로운 룰(.soar) 파일 저장/덮어쓰기
    rule_file_path = f"{save_dir}/{keyword}.soar"
    with open(rule_file_path, "w", encoding="utf-8") as f:
        f.write(new_rule)

    # 2. 업데이트된 딕셔너리(.json) 파일 저장/덮어쓰기
    dict_file_path = f"{save_dir}/intent_dictionary.json"
    with open(dict_file_path, "w", encoding="utf-8") as f:
        json.dump(intent_dictionary, f, ensure_ascii=False, indent=4)

    return {"intent_dictionary": intent_dictionary}

def NewKewordLLM(state: GraphState):

    keyword = state.get('keyword', None)
    dup_data = state.get('dup_data', None)

    system_prompt = system_prompt_initial_rule
    user_prompt = generate_initial_rules_LLM(keyword, dup_data)
    result = _call_llm(system_prompt, user_prompt)
    if result.startswith("```json"):
        result = result[7:-3].strip()
    elif result.startswith("```"):
        result = result[3:-3].strip()
    
    new_rule_topic = json.loads(result)
    return {'llm_output': new_rule_topic}


def build_soar_rule(state: dict):
    """
    Base -> Elaborate(도장찍기) -> Propose(단일 오퍼레이터 생성) -> S1(우대) -> SOS
    """

    # 1. 베이스 룰 로드
    file_path = "./soar_rule/base.soar"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            base_rule = f.read()
    else:
        base_rule = ""

    final_code = base_rule + "\n"
    llm_data = state.get('llm_output', {})
    keyword = state.get('keyword', None)

    dict_file_path = "./soar_rule/intent_dictionary.json"
    if os.path.exists(dict_file_path):
        with open(dict_file_path, "r", encoding="utf-8") as f:
            intent_dictionary = json.load(f)
    else:
        intent_dictionary = {}

    top_5 = llm_data.get('top_5_features', [])
    most_important = llm_data.get('most_important_feature', {})
    
    for idx, feature in enumerate(top_5, 1):
        final_code += _generate_elaborate_candidate_rule(feature['topic'], feature['property'], idx) + "\n"
        
    if top_5: # 조건이 하나라도 있을 때만 오퍼레이터 룰 생성
        final_code += _generate_universal_propose_rule() + "\n"
        
    # S1 Judge 룰 생성
    if most_important:
        final_code += _generate_s1_judge_rule(most_important['topic'], most_important['property']) + "\n"
        
    # SOS 룰 붙이기 (S2 깊이)
    final_code += _generate_sos_rule(top_num=1) + "\n"
    
    intent_dictionary[keyword] = top_5

    return {"rule": final_code, "intent_dictionary": intent_dictionary}

def pop_cafe_candidates(state: GraphState):
    cafe_candidates = state.get("cafe_candidates", None)
    results = state.get("results", None)
    pop_result = results[0]
    cafe_candidates.pop(pop_result)
    return {"cafe_candidates": cafe_candidates}

def loadRule_router(state: GraphState):
    route_result = state.get("rule", None)
    if route_result == "no_rule_keyword":
        result = False
    else:
        result = True
    return result

def Impasse_router(state: GraphState):
    status = state.get("status", None)
    results = state.get("results", [])

    # 1. 교착 상태일 때
    if status == "impasse":
        return "impasse"
        
    # 2. 성공했을 때 (결과 개수에 따라 분기)
    if status == "Success":
        if len(results) > 1:
            return "multiple_results"
        else:
            return "single_result"