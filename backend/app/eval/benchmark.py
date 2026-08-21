"""
Evaluation harness — measures precision/recall of the review engine.

Extended from v1 to support:
- Agent-based evaluation (not just rules)
- Labeled eval set format for past PRs
- Real-world acceptance rate tracking
- Separate eval for rules-only vs full agent pipeline
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from app.models import (
    EvalReport,
    EvalFixtureResult,
    FileDiff,
    Hunk,
    Finding,
    Severity,
    Category,
)
from app.analyzer import ReviewAnalyzer

logger = logging.getLogger(__name__)

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture_as_diff(filepath: Path) -> FileDiff:
    """Convert a fixture file into a FileDiff as if every line were added."""
    lines = filepath.read_text(encoding="utf-8").splitlines()
    diff_lines = [f"+{line}" for line in lines]
    hunk = Hunk(
        old_start=0,
        old_count=0,
        new_start=1,
        new_count=len(lines),
        lines=diff_lines,
    )
    return FileDiff(filename=filepath.name, hunks=[hunk], is_new=True)


def _load_expected(filepath: Path) -> list[dict]:
    """Load ground-truth expected findings from the JSON sidecar."""
    expected_path = filepath.with_suffix(".expected.json")
    if not expected_path.exists():
        return []
    return json.loads(expected_path.read_text(encoding="utf-8"))


def _match_finding(finding: Finding, expected: dict, tolerance: int = 3) -> bool:
    """Check whether a finding matches an expected annotation within a line tolerance."""
    line_match = abs(finding.line_start - expected["line"]) <= tolerance
    category_match = finding.category.value == expected["category"]
    return line_match and category_match


async def run_benchmark(include_agent: bool = False) -> EvalReport:
    """
    Run the analyzer against all fixtures and compute precision/recall.

    Args:
        include_agent: If True, run full agent pipeline (slower, non-deterministic).
                      If False, only run deterministic rules (fast, repeatable).
    """
    analyzer = ReviewAnalyzer()
    fixture_files = sorted(_FIXTURES_DIR.glob("*.py"))

    details: list[EvalFixtureResult] = []
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for fixture_path in fixture_files:
        expected = _load_expected(fixture_path)
        file_diff = _load_fixture_as_diff(fixture_path)

        if include_agent:
            # Full pipeline: rules + agent
            findings = await analyzer.analyze([file_diff])
        else:
            # Rules only: fast, deterministic, repeatable
            findings = analyzer._run_rules(file_diff)

        matched_expected: set[int] = set()
        matched_findings: set[int] = set()

        for fi, finding in enumerate(findings):
            for ei, exp in enumerate(expected):
                if ei not in matched_expected and _match_finding(finding, exp):
                    matched_expected.add(ei)
                    matched_findings.add(fi)
                    break

        tp = len(matched_expected)
        fp = len(findings) - len(matched_findings)
        fn = len(expected) - len(matched_expected)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0

        details.append(
            EvalFixtureResult(
                fixture=fixture_path.name,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision=round(precision, 3),
                recall=round(recall, 3),
            )
        )

        total_tp += tp
        total_fp += fp
        total_fn += fn

        logger.info(
            "Fixture %s: TP=%d FP=%d FN=%d P=%.3f R=%.3f",
            fixture_path.name, tp, fp, fn, precision, recall,
        )

    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    f1 = (
        2 * overall_precision * overall_recall / (overall_precision + overall_recall)
        if (overall_precision + overall_recall) > 0
        else 0.0
    )

    return EvalReport(
        precision=round(overall_precision, 3),
        recall=round(overall_recall, 3),
        f1=round(f1, 3),
        total_fixtures=len(fixture_files),
        details=details,
    )


# ---------------------------------------------------------------------------
# Labeled eval set format
# ---------------------------------------------------------------------------

EVAL_SET_FORMAT = """
## Labeled Eval Set Format

Each eval case is a pair of files in the fixtures/ directory:
  - `<name>.py` — The source code to review
  - `<name>.expected.json` — The ground-truth findings

### Expected JSON format:
```json
[
    {
        "line": 5,
        "category": "security",
        "severity": "critical",
        "description": "Hardcoded AWS access key"
    },
    {
        "line": 11,
        "category": "security",
        "severity": "high",
        "description": "SQL injection via f-string"
    }
]
```

### Adding new eval cases:
1. Create `fixtures/<name>.py` with the vulnerable/clean code
2. Create `fixtures/<name>.expected.json` with expected findings
3. Run `python -m app.eval.benchmark` to verify

### Matching rules:
- A finding matches an expected annotation if:
  - The line numbers are within ±3 lines of each other
  - The category (bug/security/style/performance) matches
- This tolerance accounts for differences in how rules vs LLM
  report line numbers (start of block vs specific line)
"""


# ---------------------------------------------------------------------------
# Real-world acceptance rate tracker
# ---------------------------------------------------------------------------

class AcceptanceTracker:
    """
    Tracks whether review findings are acted on by developers.

    This is a long-term quality signal: if developers consistently dismiss
    our findings, we're probably producing false positives.

    Usage:
    - When a finding is posted as a PR comment, record it.
    - When the PR is merged/closed, check if the finding was resolved.
    - Periodically compute acceptance rate.

    ASSUMPTION: This requires GitHub webhook events for issue_comment and
    pull_request (closed). Not yet wired up — this is the data model.
    """

    def __init__(self):
        self._findings: dict[str, dict[str, Any]] = {}

    def record_posted_finding(self, review_id: str, finding_id: str, pr_url: str) -> None:
        """Record that a finding was posted as a PR comment."""
        self._findings[finding_id] = {
            "review_id": review_id,
            "pr_url": pr_url,
            "posted_at": time.time(),
            "resolved": None,  # None = unknown, True = acted on, False = dismissed
        }

    def record_resolution(self, finding_id: str, was_resolved: bool) -> None:
        """Record whether a finding was acted on or dismissed."""
        if finding_id in self._findings:
            self._findings[finding_id]["resolved"] = was_resolved

    def get_acceptance_rate(self) -> dict[str, Any]:
        """Compute the acceptance rate across all tracked findings."""
        total = len(self._findings)
        resolved = sum(1 for f in self._findings.values() if f["resolved"] is True)
        dismissed = sum(1 for f in self._findings.values() if f["resolved"] is False)
        unknown = sum(1 for f in self._findings.values() if f["resolved"] is None)

        return {
            "total_posted": total,
            "resolved": resolved,
            "dismissed": dismissed,
            "unknown": unknown,
            "acceptance_rate": resolved / total if total > 0 else 0.0,
        }


# Singleton instance
acceptance_tracker = AcceptanceTracker()
