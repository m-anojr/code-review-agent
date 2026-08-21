"""
Hybrid analysis engine — orchestrates deterministic rules + agentic LLM review.

This is the upgraded analyzer that replaces the old single-shot LLM call with
the full agent loop. The existing deterministic rules are preserved as a
pre-filter: they run first (fast, free, high precision), then the agent handles
the deeper analysis.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.models import FileDiff, Finding, Severity, Category

# Existing rule engines — preserved from v1
from app.rules.secrets import check_secrets
from app.rules.sql_injection import check_sql_injection
from app.rules.exceptions import check_exceptions

# New agent + retrieval layer
from app.agent import ReviewAgent
from app.retrieval import index_file, search_index, index_past_findings

logger = logging.getLogger(__name__)


class ReviewAnalyzer:
    """
    Hybrid code review engine: deterministic rules first, then agentic LLM review.

    Pipeline:
    1. Run all deterministic rules (secrets, SQLi, exceptions) — pre-filter
    2. Index changed file into vector store for retrieval
    3. Retrieve related code context from the index
    4. Run the agent loop (ReAct with tools) for deep analysis
    5. Merge, deduplicate, and sort all findings
    """

    def __init__(self):
        self._agent = ReviewAgent()

    async def analyze(self, file_diffs: list[FileDiff]) -> list[Finding]:
        """Run the full analysis pipeline on a list of file diffs."""
        all_findings: list[Finding] = []

        # Phase 1: Index all changed files for retrieval
        for fd in file_diffs:
            full_source = _reconstruct_source(fd)
            if full_source:
                index_file(full_source, fd.filename)

        # Phase 2: Analyze each file
        for fd in file_diffs:
            # Step 2a: Deterministic rules (fast, free, high precision)
            rule_findings = self._run_rules(fd)
            all_findings.extend(rule_findings)

            # Step 2b: Retrieve related context for this file
            retrieved_context = self._get_context(fd)

            # Step 2c: Agent loop (deep LLM analysis with tools)
            agent_findings = await self._agent.review_file(
                fd, rule_findings, retrieved_context
            )
            all_findings.extend(agent_findings)

        # Phase 3: Merge and deduplicate
        all_findings = _deduplicate(all_findings)
        all_findings.sort(key=_severity_sort_key)
        return all_findings

    def _run_rules(self, file_diff: FileDiff) -> list[Finding]:
        """Run all deterministic rule checks against a single file diff."""
        findings: list[Finding] = []
        findings.extend(check_secrets(file_diff))
        findings.extend(check_sql_injection(file_diff))
        findings.extend(check_exceptions(file_diff))
        return findings

    def _get_context(self, file_diff: FileDiff) -> str:
        """Retrieve relevant code context from the vector store."""
        try:
            # Build a search query from the diff content
            added_lines = []
            for hunk in file_diff.hunks:
                for line in hunk.lines:
                    if line.startswith("+") and not line.startswith("+++"):
                        added_lines.append(line[1:].strip())

            if not added_lines:
                return ""

            # Use the first few significant added lines as the search query
            query = " ".join(added_lines[:10])
            if len(query) < 10:
                return ""

            results = search_index(query, top_k=3)
            if not results:
                return ""

            parts = []
            for r in results:
                # Don't include the file itself as context
                if r["file"] == file_diff.filename:
                    continue
                parts.append(f"--- {r['file']} (similarity: {r['score']:.2f}) ---")
                parts.append(r["content"])
                parts.append("")

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
    Remove duplicate findings covering the same lines with the same category.
    Priority: rule > agent > llm (rule findings are highest precision).
    """
    SOURCE_PRIORITY = {"rule": 0, "agent": 1, "llm": 2}
    seen: set[tuple[str, int, int, str]] = set()
    deduped: list[Finding] = []
    # Process by source priority so rules take precedence
    sorted_findings = sorted(
        findings,
        key=lambda f: SOURCE_PRIORITY.get(f.source, 3),
    )
    for f in sorted_findings:
        key = (f.file, f.line_start, f.line_end, f.category.value)
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    return deduped


def _severity_sort_key(finding: Finding) -> int:
    order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
    return order.get(finding.severity, 4)
