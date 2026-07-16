import pytest
from unittest.mock import patch, AsyncMock

from app.models import FileDiff, Hunk, Severity
from app.analyzer import ReviewAnalyzer, _deduplicate, _severity_sort_key
from app.models import Finding, Category


def _make_diff(filename: str, lines: list[str]) -> FileDiff:
    diff_lines = [f"+{line}" for line in lines]
    return FileDiff(
        filename=filename,
        hunks=[
            Hunk(old_start=0, old_count=0, new_start=1, new_count=len(lines), lines=diff_lines)
        ],
        is_new=True,
    )


class TestAnalyzer:
    @pytest.mark.asyncio
    async def test_rules_only_when_no_api_key(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            analyzer = ReviewAnalyzer()
            diff = _make_diff("test.py", ['secret = "AKIAIOSFODNN7EXAMPLE"'])
            findings = await analyzer.analyze([diff])
            assert len(findings) >= 1
            assert all(f.source == "rule" for f in findings)

    @pytest.mark.asyncio
    async def test_analyze_clean_code_no_findings(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            analyzer = ReviewAnalyzer()
            diff = _make_diff("clean.py", ["x = 42", "y = x + 1"])
            findings = await analyzer.analyze([diff])
            assert len(findings) == 0


class TestDeduplication:
    def test_deduplicates_same_location_and_category(self):
        f1 = Finding(
            file="a.py", line_start=1, line_end=1,
            severity=Severity.HIGH, category=Category.SECURITY,
            explanation="from rule", suggested_fix="fix", source="rule",
        )
        f2 = Finding(
            file="a.py", line_start=1, line_end=1,
            severity=Severity.HIGH, category=Category.SECURITY,
            explanation="from llm", suggested_fix="fix", source="llm",
        )
        result = _deduplicate([f1, f2])
        assert len(result) == 1
        assert result[0].source == "rule"  # rule takes priority

    def test_keeps_different_categories(self):
        f1 = Finding(
            file="a.py", line_start=1, line_end=1,
            severity=Severity.HIGH, category=Category.SECURITY,
            explanation="security", suggested_fix="fix", source="rule",
        )
        f2 = Finding(
            file="a.py", line_start=1, line_end=1,
            severity=Severity.MEDIUM, category=Category.BUG,
            explanation="bug", suggested_fix="fix", source="llm",
        )
        result = _deduplicate([f1, f2])
        assert len(result) == 2


class TestSeveritySort:
    def test_critical_first(self):
        findings = [
            Finding(file="a.py", line_start=1, line_end=1, severity=Severity.LOW, category=Category.STYLE, explanation="", suggested_fix="", source="rule"),
            Finding(file="a.py", line_start=2, line_end=2, severity=Severity.CRITICAL, category=Category.SECURITY, explanation="", suggested_fix="", source="rule"),
            Finding(file="a.py", line_start=3, line_end=3, severity=Severity.MEDIUM, category=Category.BUG, explanation="", suggested_fix="", source="rule"),
        ]
        findings.sort(key=_severity_sort_key)
        assert findings[0].severity == Severity.CRITICAL
        assert findings[-1].severity == Severity.LOW
