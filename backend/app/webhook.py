"""
GitHub webhook handler — receives PR events and triggers reviews.

Validates webhook signatures (HMAC-SHA256), extracts PR info, and queues
review jobs. This is the integration point for real developer workflows:
GitHub sends a POST here whenever a PR is opened or updated.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Request, HTTPException, Header

from app.config import get_settings
from app.models import WebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook HMAC-SHA256 signature.
    This prevents attackers from triggering reviews by sending fake webhook events.
    """
    if not secret:
        # ASSUMPTION: In development, webhook secret may not be configured.
        # In production, this should always be set.
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature verification")
        return True

    if not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/api/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
):
    """
    Receive GitHub webhook events for pull requests.

    Supported events:
    - pull_request (actions: opened, synchronize, reopened)

    The webhook triggers an asynchronous review of the PR.
    """
    settings = get_settings()
    body = await request.body()

    # Step 1: Verify webhook signature (defense against spoofed events)
    if not _verify_signature(body, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Step 2: Only process pull_request events
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"Event type '{x_github_event}' not handled"}

    # Step 3: Parse the payload
    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception as e:
        logger.error("Failed to parse webhook payload: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    # Step 4: Only review on relevant actions
    if payload.action not in ("opened", "synchronize", "reopened"):
        return {
            "status": "ignored",
            "reason": f"Action '{payload.action}' not handled",
        }

    # Step 5: Extract PR info and trigger review
    repo_full_name = payload.repository.get("full_name", "")
    owner, repo = repo_full_name.split("/", 1) if "/" in repo_full_name else ("", "")
    pr_number = payload.number
    pr_title = payload.pull_request.get("title", "")

    logger.info(
        "Webhook received: %s/%s PR #%d (%s) — action: %s",
        owner, repo, pr_number, pr_title, payload.action,
    )

    # Import here to avoid circular imports
    from app.main import trigger_review

    try:
        review_id = await trigger_review(owner, repo, pr_number)
        return {
            "status": "review_triggered",
            "review_id": review_id,
            "pr": f"{owner}/{repo}#{pr_number}",
        }
    except Exception as e:
        logger.error("Webhook review failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Review failed: {e}")
