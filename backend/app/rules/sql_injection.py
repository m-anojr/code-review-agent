from __future__ import annotations

import re
from app.models import Finding, Severity, Category, FileDiff

# detects string formatting or concatenation used to build SQL queries.
# covers f-strings, .format(), %-formatting, and raw concatenation with SQL keywords.
_SQL_KEYWORDS = r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE|UNION)\b"

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "f-string SQL query",
        re.compile(
            rf"""f(?:"|').*{_SQL_KEYWORDS}.*\{{.*\}}""",
            re.IGNORECASE,
        ),
    ),
    (
        ".format() SQL query",
        re.compile(
            rf"""(?:"|').*{_SQL_KEYWORDS}.*(?:"|')\s*\.format\(""",
            re.IGNORECASE,
        ),
    ),
    (
        "%-formatted SQL query",
        re.compile(
            rf"""(?:"|').*{_SQL_KEYWORDS}.*%[sd].*(?:"|')\s*%\s*""",
            re.IGNORECASE,
        ),
    ),
    (
        "string concatenation in SQL query",
        re.compile(
            rf"""(?:"|').*{_SQL_KEYWORDS}.*(?:"|')\s*\+\s*""",
            re.IGNORECASE,
        ),
    ),
]


def check_sql_injection(file_diff: FileDiff) -> list[Finding]:
    """Detect potential SQL injection via string interpolation into queries."""
    findings: list[Finding] = []
    for hunk in file_diff.hunks:
        line_num = hunk.new_start
        for line in hunk.lines:
            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:]
                for label, pattern in _PATTERNS:
                    if pattern.search(content):
                        findings.append(
                            Finding(
                                file=file_diff.filename,
                                line_start=line_num,
                                line_end=line_num,
                                severity=Severity.HIGH,
                                category=Category.SECURITY,
                                explanation=f"Potential SQL injection: {label}. User input may be interpolated directly into a SQL query.",
                                suggested_fix="Use parameterized queries or an ORM instead of string interpolation.",
                                source="rule",
                            )
                        )
                        break
            if not line.startswith("-"):
                line_num += 1

    return findings
