from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver
from agent.state import PRReviewState
from agent.nodes import analysis_node, suggestion_node, judge_node, human_review_node, patch_node

def route_after_review(state):
    if state["human_approved"]:
        return "patch"
    
    return "end"

builder = StateGraph(PRReviewState)

# Nodes
builder.add_node("analyze", analysis_node)
builder.add_node("suggestion", suggestion_node)
builder.add_node("judge", judge_node)
builder.add_node("human_review", human_review_node)
builder.add_node("patch", patch_node)

# Edges
builder.add_edge(START, "analyze")
builder.add_edge("analyze", "suggestion")
builder.add_edge("suggestion", "judge")
builder.add_edge("judge", "human_review")
builder.add_edge("suggestion", "human_review")

# Conditional Edges
builder.add_conditional_edges("human_review", route_after_review,{
    "patch": "patch",
    "end": END
    })

builder.add_edge("patch", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)