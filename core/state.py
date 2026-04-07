from typing import TypedDict, Dict, Any, List, Optional

class GraphState(TypedDict):
    user_query: Any
    keyword: Any                
    cafe_candidates: Any       
    rule: Any                     
    intent_dictionary: Any       
    cafe_orDepth: Any             
    final_cafe: Any             
    llm_intent_dict: Any        
    llm_output: Any             
    status: Any                  
    dup_data: Any
    results: List