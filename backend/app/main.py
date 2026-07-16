from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import ReviewRequest, ReviewSummary, ReviewDetail
from app.github_client import GitHubClient
from app.analyzer import ReviewAnalyzer
from app import db

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(title="Code Review Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = ReviewAnalyzer()


@app.post("/api/reviews", response_model=ReviewDetail)
async def create_review(request: ReviewRequest):
    """Trigger a code review for a GitHub pull request."""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token or token.startswith("ghp_xxxx"):
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN not configured. Set it in .env.")

    client = GitHubClient(token)
    try:
        pr_info = await client.get_pr_info(request.owner, request.repo, request.pr_number)
        pr_title = pr_info.get("title", "")
        file_diffs = await client.fetch_pr_diff(request.owner, request.repo, request.pr_number)
    except Exception as e:
        logger.error("Failed to fetch PR: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch PR from GitHub: {e}")
    finally:
        await client.close()

    if not file_diffs:
        raise HTTPException(status_code=400, detail="PR has no file changes.")

    findings = await analyzer.analyze(file_diffs)

    review_id = await db.save_review(
        owner=request.owner,
        repo=request.repo,
        pr_number=request.pr_number,
        pr_title=pr_title,
        findings=findings,
        file_diffs=file_diffs,
        files_analyzed=len(file_diffs),
    )

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
