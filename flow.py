from langgraph.graph import StateGraph, END
from core.state import GraphState 
from node import (
    start_node,
    select_keyword,
    loadRule,
    recommendation_soar,
    view_intent_dictionary,
    ImpasseLLM,
    update_rule,
    update_intent_dictionary,
    NewKewordLLM,
    build_soar_rule,
    loadRule_router,
    Impasse_router,
    pop_cafe_candidates
)


def graph_flow():
    workflow = StateGraph(GraphState)
    workflow.add_node("start_node", start_node)
    workflow.add_node("select_keyword", select_keyword)
    workflow.add_node("loadRule", loadRule)
    workflow.add_node("recommendation_soar", recommendation_soar)
    workflow.add_node("view_intent_dictionary", view_intent_dictionary)
    workflow.add_node("ImpasseLLM", ImpasseLLM)
    workflow.add_node("update_rule", update_rule)
    workflow.add_node("update_intent_dictionary", update_intent_dictionary)
    workflow.add_node("NewKewordLLM", NewKewordLLM)
    workflow.add_node("build_rule", build_soar_rule)
    workflow.add_node("pop_cafe_candidates", pop_cafe_candidates)

    workflow.set_entry_point("start_node")
    workflow.add_edge("start_node", "select_keyword")
    workflow.add_edge("select_keyword", "loadRule")
    workflow.add_conditional_edges(
        "loadRule",
        loadRule_router,
        {
            True: "recommendation_soar",
            False: "NewKewordLLM"
        }
    )
    workflow.add_conditional_edges(
        "recommendation_soar",
        Impasse_router,
        {
            "multiple_results": END,
            "single_result": "pop_cafe_candidates",
            "impasse": "view_intent_dictionary"
        }
    )
    workflow.add_edge("view_intent_dictionary", "ImpasseLLM")
    workflow.add_edge("ImpasseLLM", "update_rule")
    workflow.add_edge("update_rule", "update_intent_dictionary")
    workflow.add_edge("update_intent_dictionary", "loadRule")
    workflow.add_edge("NewKewordLLM", "build_rule")
    workflow.add_edge("build_rule", "update_intent_dictionary")
    workflow.add_edge("pop_cafe_candidates", "loadRule")
    
    app = workflow.compile()
    return app