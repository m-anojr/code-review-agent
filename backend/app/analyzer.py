"""
Hybrid analysis engine — orchestrates deterministic rules + agentic LLM review.

This is the upgraded analyzer that replaces the old single-shot LLM call with
the full agent loop. The existing deterministic rules are preserved as a
pre-filter: they run first (fast, free, high precision), then the agent handles
the deeper analysis.
"""
from __future__ import annotations

import logging

from app.config import get_settings
from app.models import FileDiff, Finding, Severity

# Existing rule engines — preserved from v1
from app.rules.secrets import check_secrets
from app.rules.sql_injection import check_sql_injection
from app.rules.exceptions import check_exceptions

# New agent + retrieval layer
from app.agent import ReviewAgent, ReviewBudget
from app.retrieval import index_file, search_index, review_index_scope

logger = logging.getLogger(__name__)


class ReviewAnalyzer:
    """
    Hybrid code review engine: deterministic rules first, then agentic LLM review.

    Pipeline:
    1. Run all deterministic rules (secrets, SQLi, exceptions) — pre-filter
    2. Build an isolated index from changed files for context retrieval
    3. Retrieve related code context from the index
    4. Run the agent loop (ReAct with tools) for deep analysis
    5. Merge, deduplicate, and sort all findings
    """

    def __init__(self):
        self._agent = ReviewAgent()

    async def analyze(self, file_diffs: list[FileDiff]) -> list[Finding]:
        """Run the full analysis pipeline on a list of file diffs."""
        all_findings: list[Finding] = []
        settings = get_settings()
        budget = ReviewBudget(limit=settings.AGENT_TOKEN_BUDGET)

        # Keep retrieval isolated to this PR so another concurrent review cannot
        # leak stale code into the model's context.
        with review_index_scope():
            for fd in file_diffs:
                full_source = _reconstruct_source(fd)
                if full_source:
                    index_file(full_source, fd.filename)

            for fd in file_diffs:
                rule_findings = self._run_rules(fd)
                all_findings.extend(rule_findings)

                retrieved_context = self._get_context(fd)
                agent_findings = await self._agent.review_file(
                    fd, rule_findings, retrieved_context, budget=budget
                )
                all_findings.extend(agent_findings)

        # Phase 3: Merge and deduplicate
        all_findings = _deduplicate(all_findings)
        all_findings.sort(key=_severity_sort_key)
        logger.info("Review agent token usage: %d/%d", budget.used, budget.limit)
        return all_findings

    def _run_rules(self, file_diff: FileDiff) -> list[Finding]:
        """Run all deterministic rule checks against a single file diff."""
        findings: list[Finding] = []
        findings.extend(check_secrets(file_diff))
        findings.extend(check_sql_injection(file_diff))
        findings.extend(check_exceptions(file_diff))
        return findings

    def _get_context(self, file_diff: FileDiff) -> str:
        """Retrieve relevant context from other changed files in this PR."""
        try:
            added_lines = []
            for hunk in file_diff.hunks:
                for line in hunk.lines:
                    if line.startswith("+") and not line.startswith("+++"):
                        added_lines.append(line[1:].strip())

            if not added_lines:
                return ""

            query = " ".join(added_lines[:40])[:4000]
            if len(query) < 10:
                return ""

            results = search_index(query, top_k=12)
            if not results:
                return ""

            parts = []
            included_files: set[str] = set()
            for r in results:
                if r["file"] == file_diff.filename or r["file"] in included_files:
                    continue
                included_files.add(r["file"])
                parts.append(f"--- {r['file']} (code relevance: {r['score']:.2f}) ---")
                parts.append(r["content"])
                parts.append("")
                if len(included_files) == 4:
                    break

            return "\n".join(parts) if parts else ""
        except Exception as e:
            logger.debug("Context retrieval failed: %s", e)
            return ""


def _reconstruct_source(file_diff: FileDiff) -> str:
    """
    Reconstruct the new version of a file from its diff.
    Only includes added and context lines (the 'after' state).
    """
    lines = []
    for hunk in file_diff.hunks:
        for line in hunk.lines:
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(line[1:])
            elif not line.startswith("-"):
                # Context line
                if line.startswith(" "):
                    lines.append(line[1:])
                else:
                    lines.append(line)
    return "\n".join(lines)


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    """
    Remove overlapping findings on the same file/category.
    Priority: rule > agent > llm (rule findings are highest precision).
    """
    SOURCE_PRIORITY = {"rule": 0, "agent": 1, "llm": 2}
    deduped: list[Finding] = []
    # Process by source priority so rules take precedence
    sorted_findings = sorted(
        findings,
        key=lambda f: SOURCE_PRIORITY.get(f.source, 3),
    )
    for f in sorted_findings:
        duplicate = any(
            existing.file == f.file
            and existing.category == f.category
            and existing.line_start <= f.line_end
            and f.line_start <= existing.line_end
            for existing in deduped
        )
        if not duplicate:
            deduped.append(f)
    return deduped


def _severity_sort_key(finding: Finding) -> tuple[int, str, int]:
    order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
    return order.get(finding.severity, 4), finding.file, finding.line_start
