from __future__ import annotations

import re
from app.models import Finding, Severity, Category, FileDiff

# bare except clause with no exception type
_BARE_EXCEPT = re.compile(r"^\s*except\s*:")

# except that catches broadly and does nothing (pass on the next non-blank line)
_BROAD_EXCEPT = re.compile(r"^\s*except\s+(?:Exception|BaseException)\s*(?:as\s+\w+)?\s*:")


def check_exceptions(file_diff: FileDiff) -> list[Finding]:
    """Detect bare except clauses and swallowed exceptions."""
    findings: list[Finding] = []
    for hunk in file_diff.hunks:
        added_lines: list[tuple[int, str]] = []
        line_num = hunk.new_start
        for line in hunk.lines:
            if line.startswith("+") and not line.startswith("+++"):
                added_lines.append((line_num, line[1:]))
            if not line.startswith("-"):
                line_num += 1

        for i, (ln, content) in enumerate(added_lines):
            if _BARE_EXCEPT.match(content):
                findings.append(
                    Finding(
                        file=file_diff.filename,
                        line_start=ln,
                        line_end=ln,
                        severity=Severity.MEDIUM,
                        category=Category.BUG,
                        explanation="Bare except clause catches all exceptions including KeyboardInterrupt and SystemExit.",
                        suggested_fix="Catch a specific exception type, e.g. `except ValueError:` or at minimum `except Exception:`.",
                        source="rule",
                    )
                )
            elif _BROAD_EXCEPT.match(content):
                # check if the body is just `pass`
                next_content_line = _next_nonblank(added_lines, i + 1)
                if next_content_line is not None and next_content_line.strip() == "pass":
                    findings.append(
                        Finding(
                            file=file_diff.filename,
                            line_start=ln,
                            line_end=ln,
                            severity=Severity.MEDIUM,
                            category=Category.BUG,
                            explanation="Exception is caught and silently swallowed with `pass`. Errors will be hidden.",
                            suggested_fix="Log the exception or re-raise it. Silently swallowing exceptions makes debugging very difficult.",
                            source="rule",
                        )
                    )

    return findings


def _next_nonblank(lines: list[tuple[int, str]], start: int) -> str | None:
    """Return the content of the next non-blank line, or None if none exists."""
    for j in range(start, len(lines)):
        stripped = lines[j][1].strip()
        if stripped:
            return stripped
    return None
