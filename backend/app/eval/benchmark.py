from __future__ import annotations

import json
import logging
import os
from pathlib import Path

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


async def run_benchmark() -> EvalReport:
    """Run the analyzer against all fixtures and compute precision/recall."""
    analyzer = ReviewAnalyzer()
    fixture_files = sorted(_FIXTURES_DIR.glob("*.py"))

    details: list[EvalFixtureResult] = []
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for fixture_path in fixture_files:
        expected = _load_expected(fixture_path)
        file_diff = _load_fixture_as_diff(fixture_path)

        # only run rule-based checks for eval (LLM results are non-deterministic)
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
