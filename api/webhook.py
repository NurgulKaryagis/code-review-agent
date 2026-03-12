import sys
import os
import uuid

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from agent.graph import graph


router = APIRouter()


@router.post("/webhook")
async def github_webhook(payload: dict):
    # Only handle pull_request events
    event_type = payload.get("action")
    if "pull_request" not in payload:
        raise HTTPException(status_code=400, detail="Not a pull_request event")

    # Only process opened or synchronize actions
    if event_type not in ("opened", "synchronize"):
        return {"message": f"Ignored action: {event_type}"}

    # Extract PR details from payload
    pr = payload["pull_request"]
    pr_id = pr["number"]
    pr_url = pr["html_url"]

    # Build initial state
    thread_id = str(uuid.uuid4())
    initial_state = {
        "pr_id": pr_id,
        "pr_url": pr_url,
        "thread_id": thread_id,
        "pr_review_steps": [],
    }
    config = {"configurable": {"thread_id": thread_id}}

    # Invoke the graph
    result = graph.invoke(initial_state, config=config)

    return {
        "thread_id": config["configurable"]["thread_id"],
        "pr_id": pr_id,
        "pr_url": pr_url,
        "suggestion_status": result.get("suggestion_status"),
        "suggested_codes": result.get("suggested_codes"),
        "judge_scores": result.get("judge_scores"),
        "judge_status": result.get("judge_status"),
        "pr_review_steps": result.get("pr_review_steps"),
    }


@router.post("/approve")
async def approve_review(thread_id: str, approved: bool):
    config = {"configurable": {"thread_id": thread_id}}
    
    result = graph.invoke(
        Command(resume=approved),
        config=config
    )
    
    return {
        "patch_status": result.get("patch_status"),
        "judge_scores": result.get("judge_scores"),
        "pr_review_steps": result.get("pr_review_steps"),
    }