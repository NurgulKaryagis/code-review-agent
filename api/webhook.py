import hashlib
import hmac
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from langgraph.types import Command

from agent.graph import graph
from api.schemas import WebhookPayload
from config.settings import WEBHOOK_SECRET

router = APIRouter()


async def _verify_github_signature(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
) -> None:
    if not WEBHOOK_SECRET:
        return
    if x_hub_signature_256 is None:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
    body = await request.body()
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/webhook")
async def github_webhook(
    request: Request,
    payload: WebhookPayload,
    _: None = Depends(_verify_github_signature),
):
    if payload.action not in ("opened", "synchronize"):
        return {"message": f"Ignored action: {payload.action}"}

    pr_id = payload.pull_request.number
    pr_url = str(payload.pull_request.html_url)

    thread_id = str(uuid.uuid4())
    initial_state = {
        "pr_id": pr_id,
        "pr_url": pr_url,
        "thread_id": thread_id,
        "pr_review_steps": [],
    }
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke(initial_state, config=config)

    return {
        "thread_id": thread_id,
        "pr_id": pr_id,
        "pr_url": pr_url,
        "judge_scores": result.get("judge_scores"),
        "judge_status": result.get("judge_status"),
        "pr_review_steps": result.get("pr_review_steps"),
    }


@router.post("/approve")
async def approve_review(request: Request, thread_id: str, approved: bool):
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke(
        Command(resume=approved),
        config=config,
    )

    return {
        "pr_result": result.get("pr_result"),
        "judge_scores": result.get("judge_scores"),
        "pr_review_steps": result.get("pr_review_steps"),
    }