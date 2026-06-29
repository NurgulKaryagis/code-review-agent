from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import PRReviewState
from agent.nodes import (
    supervisor_node,
    code_analyst_node,
    implementation_node,
    generate_tests_node,
    security_agent_node,
    review_node,
    judge_node,
    human_review_node,
    pr_agent_node,
)


def route_after_human_review(state: PRReviewState) -> str:
    return "pr_agent" if state["human_approved"] else END


builder = StateGraph(PRReviewState)

# Nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("code_analyst", code_analyst_node)
builder.add_node("implementation", implementation_node)
builder.add_node("test_agent", generate_tests_node)
builder.add_node("security_agent", security_agent_node)
builder.add_node("review", review_node)
builder.add_node("judge", judge_node)
builder.add_node("human_review", human_review_node)
builder.add_node("pr_agent", pr_agent_node)

# Linear flow
builder.add_edge(START, "supervisor")
builder.add_edge("supervisor", "code_analyst")
builder.add_edge("code_analyst", "implementation")

# Fan-out: implementation → test_agent and security_agent run in parallel
builder.add_edge("implementation", "test_agent")
builder.add_edge("implementation", "security_agent")

# Fan-in: review waits for both parallel nodes to complete
builder.add_edge("test_agent", "review")
builder.add_edge("security_agent", "review")

# Continue linear
builder.add_edge("review", "judge")
builder.add_edge("judge", "human_review")

# HITL: pr_agent only runs on approval
builder.add_conditional_edges("human_review", route_after_human_review)

builder.add_edge("pr_agent", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)