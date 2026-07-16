from __future__ import annotations

import re
from typing import Any

import httpx

from app.models import FileDiff, Hunk, Finding, Severity

_DIFF_FILE_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+?)$")
_HUNK_HEADER = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)")
_MAX_DIFF_LINES_PER_FILE = 3000


class GitHubClient:
    """Fetches PR diffs and optionally posts review comments via the GitHub REST API."""

    def __init__(self, token: str):
        self._token = token
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_pr_info(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """Fetch basic PR metadata."""
        resp = await self._client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        resp.raise_for_status()
        return resp.json()

    async def fetch_pr_diff(self, owner: str, repo: str, pr_number: int) -> list[FileDiff]:
        """Fetch and parse the unified diff for a pull request."""
        resp = await self._client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        resp.raise_for_status()
        return parse_diff(resp.text)

    async def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        findings: list[Finding],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Post findings as a PR review. In dry-run mode, returns the payload without posting."""
        comments = []
        for f in findings:
            if f.severity in (Severity.CRITICAL, Severity.HIGH):
                body = f"**[{f.severity.value.upper()}] {f.category.value}**: {f.explanation}"
                if f.suggested_fix:
                    body += f"\n\nSuggested fix: {f.suggested_fix}"
                comment: dict[str, Any] = {
                    "path": f.file,
                    "line": f.line_end,
                    "body": body,
                }
                if f.line_start != f.line_end:
                    comment["start_line"] = f.line_start
                comments.append(comment)

        payload = {
            "event": "COMMENT",
            "body": f"Code review: {len(findings)} finding(s) across this PR.",
            "comments": comments,
        }

        if dry_run:
            return {"dry_run": True, "payload": payload}

        resp = await self._client.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


def parse_diff(raw: str) -> list[FileDiff]:
    """Parse a unified diff string into structured FileDiff objects."""
    files: list[FileDiff] = []
    current_file: dict[str, Any] | None = None
    current_hunks: list[Hunk] = []
    current_lines: list[str] = []
    current_hunk_match: re.Match[str] | None = None
    header_lines: list[str] = []
    diff_line_count = 0

    def _flush_hunk() -> None:
        nonlocal current_hunk_match, current_lines
        if current_hunk_match and current_lines:
            m = current_hunk_match
            current_hunks.append(
                Hunk(
                    old_start=int(m.group(1)),
                    old_count=int(m.group(2) or 1),
                    new_start=int(m.group(3)),
                    new_count=int(m.group(4) or 1),
                    lines=current_lines,
                    header=m.group(5).strip(),
                )
            )
        current_lines = []
        current_hunk_match = None

    def _flush_file() -> None:
        nonlocal current_file, current_hunks, header_lines, diff_line_count
        _flush_hunk()
        if current_file and current_hunks:
            is_new = any("new file mode" in h for h in header_lines)
            is_deleted = any("deleted file mode" in h for h in header_lines)
            files.append(
                FileDiff(
                    filename=current_file["new"],
                    old_filename=current_file["old"] if current_file["old"] != current_file["new"] else None,
                    hunks=current_hunks,
                    is_new=is_new,
                    is_deleted=is_deleted,
                    raw_header="\n".join(header_lines),
                )
            )
        current_file = None
        current_hunks = []
        header_lines = []
        diff_line_count = 0

    for line in raw.splitlines():
        file_match = _DIFF_FILE_HEADER.match(line)
        if file_match:
            _flush_file()
            current_file = {"old": file_match.group(1), "new": file_match.group(2)}
            header_lines.append(line)
            continue

        if current_file is None:
            continue

        hunk_match = _HUNK_HEADER.match(line)
        if hunk_match:
            _flush_hunk()
            current_hunk_match = hunk_match
            diff_line_count = 0
            continue

        if current_hunk_match:
            diff_line_count += 1
            if diff_line_count <= _MAX_DIFF_LINES_PER_FILE:
                current_lines.append(line)
        else:
            header_lines.append(line)

    _flush_file()
    return files
