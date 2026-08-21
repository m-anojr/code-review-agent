"""
FastAPI application — main entry point.

Integrates all subsystems:
- REST API for manual review submission and listing
- Webhook endpoint for GitHub PR events
- Rate limiting and guardrails
- Evaluation benchmark
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models import ReviewRequest, ReviewSummary, ReviewDetail
from app.github_client import GitHubClient
from app.analyzer import ReviewAnalyzer
from app.guardrails import rate_limiter, cost_tracker, review_monitor
from app.webhook import router as webhook_router
from app import db

load_dotenv()

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    logger.info("Database initialized")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("Agent max iterations: %d", settings.AGENT_MAX_ITERATIONS)
    logger.info("Confidence threshold: %.2f", settings.AGENT_CONFIDENCE_THRESHOLD)
    yield


app = FastAPI(
    title="Agentic AI Code Review Agent",
    version="2.0.0",
    description="Production-grade code review agent with agentic reasoning, tool use, and retrieval.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register webhook routes
app.include_router(webhook_router)

# Initialize the analyzer
analyzer = ReviewAnalyzer()


# ---------------------------------------------------------------------------
# Rate limiting middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to review submission endpoints."""
    if request.url.path in ("/api/reviews",) and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.check(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please wait before submitting another review.",
                    "remaining": 0,
                },
            )
    return await call_next(request)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/reviews", response_model=ReviewDetail)
async def create_review(request: ReviewRequest):
    """Trigger an agentic code review for a GitHub pull request."""
    review_id = await trigger_review(request.owner, request.repo, request.pr_number)
    return await db.get_review(review_id)


@app.get("/api/reviews", response_model=list[ReviewSummary])
async def list_reviews():
    """List all past reviews with summary statistics."""
    return await db.get_reviews()


@app.get("/api/reviews/{review_id}", response_model=ReviewDetail)
async def get_review(review_id: str):
    """Get full details for a single review."""
    review = await db.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    return review


@app.get("/api/eval")
async def get_eval_report():
    """Run the evaluation benchmark and return results."""
    try:
        from app.eval.benchmark import run_benchmark
        report = await run_benchmark()
        return report.model_dump()
    except Exception as e:
        logger.error("Eval failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint with system status."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "agent_config": {
            "max_iterations": settings.AGENT_MAX_ITERATIONS,
            "confidence_threshold": settings.AGENT_CONFIDENCE_THRESHOLD,
            "token_budget": settings.AGENT_TOKEN_BUDGET,
        },
        "rate_limit_remaining": rate_limiter.remaining(),
        "monitor_stats": review_monitor.get_stats(),
    }


# ---------------------------------------------------------------------------
# Core review trigger — used by both REST API and webhook
# ---------------------------------------------------------------------------

async def trigger_review(owner: str, repo: str, pr_number: int) -> str:
    """
    Trigger a full agentic review of a pull request.
    Shared logic used by both the REST API and the webhook handler.
    Returns the review ID.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token or token.startswith("ghp_xxxx"):
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN not configured. Set it in .env.")

    client = GitHubClient(token)
    try:
        pr_info = await client.get_pr_info(owner, repo, pr_number)
        pr_title = pr_info.get("title", "")
        file_diffs = await client.fetch_pr_diff(owner, repo, pr_number)
    except Exception as e:
        logger.error("Failed to fetch PR: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch PR from GitHub: {e}")
    finally:
        await client.close()

    if not file_diffs:
        raise HTTPException(status_code=400, detail="PR has no file changes.")

    # Track costs for this review
    review_id_temp = f"{owner}/{repo}#{pr_number}"
    cost_tracker.start_review(review_id_temp)

    # Run the full analysis pipeline
    findings = await analyzer.analyze(file_diffs)

    # Record monitoring stats
    rule_count = sum(1 for f in findings if f.source == "rule")
    agent_count = sum(1 for f in findings if f.source == "agent")
    review_monitor.record(rule_count, agent_count)

    # Persist to database
    review_id = await db.save_review(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        pr_title=pr_title,
        findings=findings,
        file_diffs=file_diffs,
        files_analyzed=len(file_diffs),
    )

    cost_tracker.finish_review(review_id_temp)
    logger.info(
        "Review %s complete: %d rule findings, %d agent findings",
        review_id, rule_count, agent_count,
    )

    return review_id
