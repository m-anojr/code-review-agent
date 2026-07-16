from __future__ import annotations

import re
from app.models import Finding, Severity, Category, FileDiff

# patterns that strongly suggest hardcoded secrets
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "AWS access key",
        re.compile(r"""(?:"|')?(AKIA[0-9A-Z]{16})(?:"|')?"""),
    ),
    (
        "AWS secret key",
        re.compile(
            r"""(?:aws_secret_access_key|secret_key)\s*[=:]\s*(?:"|')([A-Za-z0-9/+=]{40})(?:"|')""",
            re.IGNORECASE,
        ),
    ),
    (
        "generic API key assignment",
        re.compile(
            r"""(?:api[_-]?key|apikey|secret|token|password|passwd|credentials)\s*[=:]\s*(?:"|')([A-Za-z0-9_\-/+=]{16,})(?:"|')""",
            re.IGNORECASE,
        ),
    ),
    (
        "private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"),
    ),
    (
        "GitHub personal access token",
        re.compile(r"""(?:"|')?(ghp_[A-Za-z0-9]{36})(?:"|')?"""),
    ),
    (
        "generic high-entropy hex secret",
        re.compile(
            r"""(?:secret|token|key|password)\s*[=:]\s*(?:"|')?([0-9a-f]{32,})(?:"|')?""",
            re.IGNORECASE,
        ),
    ),
]

# filenames where secrets are expected and should not be flagged
_SAFE_FILENAMES = {".env.example", ".env.template", ".env.sample"}


def check_secrets(file_diff: FileDiff) -> list[Finding]:
    """Scan added lines for hardcoded secrets and API keys."""
    basename = file_diff.filename.rsplit("/", 1)[-1] if "/" in file_diff.filename else file_diff.filename
    if basename in _SAFE_FILENAMES:
        return []

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
                                severity=Severity.CRITICAL,
                                category=Category.SECURITY,
                                explanation=f"Possible hardcoded secret detected: {label}.",
                                suggested_fix="Move this value to an environment variable or secrets manager.",
                                source="rule",
                            )
                        )
                        break  # one finding per line is enough
            # only increment line number for added or context lines
            if not line.startswith("-"):
                line_num += 1

    return findings
