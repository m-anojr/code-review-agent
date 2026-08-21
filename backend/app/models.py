"""
Domain models — shared across the entire application.

Extended from v1 to support:
- Agent source type (in addition to rule/llm)
- Confidence scores on findings
- Webhook event models
"""
from __future__ import annotations

import enum
from datetime import datetime
from pydantic import BaseModel, Field


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, enum.Enum):
    BUG = "bug"
    SECURITY = "security"
    STYLE = "style"
    PERFORMANCE = "performance"


class ReviewRequest(BaseModel):
    owner: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    pr_number: int = Field(..., gt=0)


class Finding(BaseModel):
    file: str
    line_start: int
    line_end: int
    severity: Severity
    category: Category
    explanation: str
    suggested_fix: str
    source: str = Field(..., pattern=r"^(rule|llm|agent)$")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning_trace: str = ""  # Agent's reasoning for this finding


class Hunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]
    header: str = ""


class FileDiff(BaseModel):
    filename: str
    old_filename: str | None = None
    hunks: list[Hunk]
    is_new: bool = False
    is_deleted: bool = False
    raw_header: str = ""


class ReviewSummary(BaseModel):
    id: str
    owner: str
    repo: str
    pr_number: int
    pr_title: str = ""
    created_at: datetime
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    files_analyzed: int = 0


class ReviewDetail(BaseModel):
    summary: ReviewSummary
    findings: list[Finding]
    file_diffs: list[FileDiff] = []


class EvalFixtureResult(BaseModel):
    fixture: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float


class EvalReport(BaseModel):
    precision: float
    recall: float
    f1: float
    total_fixtures: int
    details: list[EvalFixtureResult]


# --- Webhook models ---

class WebhookPayload(BaseModel):
    """Minimal model for GitHub PR webhook events."""
    action: str  # opened, synchronize, reopened
    number: int  # PR number
    pull_request: dict  # Full PR object from GitHub
    repository: dict  # Repository info
