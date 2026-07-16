from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.models import Finding, ReviewSummary, ReviewDetail, FileDiff, Severity

_DB_PATH = os.getenv("DB_PATH", "reviews.db")


async def init_db() -> None:
    """Create the reviews table if it does not exist."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                repo TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                pr_title TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                findings_json TEXT NOT NULL,
                file_diffs_json TEXT NOT NULL DEFAULT '[]',
                files_analyzed INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await db.commit()


async def save_review(
    owner: str,
    repo: str,
    pr_number: int,
    pr_title: str,
    findings: list[Finding],
    file_diffs: list[FileDiff],
    files_analyzed: int,
) -> str:
    """Persist a review and return its ID."""
    review_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    findings_json = json.dumps([f.model_dump() for f in findings])
    diffs_json = json.dumps([d.model_dump() for d in file_diffs])

    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO reviews (id, owner, repo, pr_number, pr_title, created_at, findings_json, file_diffs_json, files_analyzed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (review_id, owner, repo, pr_number, pr_title, now, findings_json, diffs_json, files_analyzed),
        )
        await db.commit()

    return review_id


async def get_reviews() -> list[ReviewSummary]:
    """Return all reviews ordered by creation date descending."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, owner, repo, pr_number, pr_title, created_at, findings_json, files_analyzed FROM reviews ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()

    summaries = []
    for row in rows:
        findings = [Finding(**f) for f in json.loads(row["findings_json"])]
        counts = _count_severities(findings)
        summaries.append(
            ReviewSummary(
                id=row["id"],
                owner=row["owner"],
                repo=row["repo"],
                pr_number=row["pr_number"],
                pr_title=row["pr_title"],
                created_at=datetime.fromisoformat(row["created_at"]),
                files_analyzed=row["files_analyzed"],
                **counts,
            )
        )
    return summaries


async def get_review(review_id: str) -> ReviewDetail | None:
    """Return full detail for a single review, or None if not found."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, owner, repo, pr_number, pr_title, created_at, findings_json, file_diffs_json, files_analyzed FROM reviews WHERE id = ?",
            (review_id,),
        )
        row = await cursor.fetchone()

    if not row:
        return None

    findings = [Finding(**f) for f in json.loads(row["findings_json"])]
    file_diffs = [FileDiff(**d) for d in json.loads(row["file_diffs_json"])]
    counts = _count_severities(findings)

    summary = ReviewSummary(
        id=row["id"],
        owner=row["owner"],
        repo=row["repo"],
        pr_number=row["pr_number"],
        pr_title=row["pr_title"],
        created_at=datetime.fromisoformat(row["created_at"]),
        files_analyzed=row["files_analyzed"],
        **counts,
    )
    return ReviewDetail(summary=summary, findings=findings, file_diffs=file_diffs)


def _count_severities(findings: list[Finding]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f.severity.value] += 1
    return counts
