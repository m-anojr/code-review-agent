from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.models import FileDiff, Finding, Severity, Category

from app.rules.secrets import check_secrets
from app.rules.sql_injection import check_sql_injection
from app.rules.exceptions import check_exceptions

logger = logging.getLogger(__name__)

_CONTEXT_LINES = 10
_MAX_HUNK_LINES_FOR_LLM = 500

_FINDING_TOOL = {
    "type": "function",
    "function": {
        "name": "report_findings",
        "description": "Report code review findings for the given diff. Return an empty list if no issues are found.",
        "parameters": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line_start": {"type": "integer"},
                            "line_end": {"type": "integer"},
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "high", "medium", "low"],
                            },
                            "category": {
                                "type": "string",
                                "enum": ["bug", "security", "style", "performance"],
                            },
                            "explanation": {"type": "string"},
                            "suggested_fix": {"type": "string"},
                        },
                        "required": [
                            "file",
                            "line_start",
                            "line_end",
                            "severity",
                            "category",
                            "explanation",
                            "suggested_fix",
                        ],
                    },
                }
            },
            "required": ["findings"],
        },
    }
}


class ReviewAnalyzer:
    """Hybrid code review engine: deterministic rules first, then LLM analysis."""

    def __init__(self):
        self._gemini_client = None
        self._or_client = None
        
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        
        try:
            from openai import AsyncOpenAI
            if self.gemini_key:
                self._gemini_client = AsyncOpenAI(
                    api_key=self.gemini_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
            if self.groq_key:
                self._groq_client = AsyncOpenAI(
                    api_key=self.groq_key,
                    base_url="https://api.groq.com/openai/v1"
                )
        except Exception as e:
            logger.warning("Failed to initialize OpenAI clients: %s", e)

    async def analyze(self, file_diffs: list[FileDiff]) -> list[Finding]:
        """Run the full analysis pipeline on a list of file diffs."""
        all_findings: list[Finding] = []

        for fd in file_diffs:
            rule_findings = self._run_rules(fd)
            all_findings.extend(rule_findings)

            llm_findings = await self._run_llm(fd, rule_findings)
            all_findings.extend(llm_findings)

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

    async def _run_llm(self, file_diff: FileDiff, rule_findings: list[Finding]) -> list[Finding]:
        """Use the LLM API to review code for logic bugs, design issues, etc."""
        if not self._gemini_client and not self._or_client:
            return []

        diff_text = _format_diff_for_llm(file_diff)
        if not diff_text.strip():
            return []

        existing_issues = ""
        if rule_findings:
            items = [
                f"- Line {f.line_start}: [{f.severity.value}] {f.explanation}"
                for f in rule_findings
            ]
            existing_issues = (
                "\n\nThe following issues have already been detected by static rules. "
                "Do not duplicate these. You may reference them if relevant to a broader issue.\n"
                + "\n".join(items)
            )

        prompt = (
            f"Review the following code diff from file `{file_diff.filename}`. "
            "Look for logic bugs, security vulnerabilities, performance issues, "
            "and significant code quality problems. Focus on non-obvious issues "
            "that a static rule would miss. Do not flag minor style preferences. "
            "If the code looks correct, return an empty findings list."
            f"{existing_issues}\n\n"
            f"```diff\n{diff_text}\n```"
        )

        messages = [{"role": "user", "content": prompt}]
        
        # Try Gemini API first
        if self._gemini_client:
            try:
                response = await self._gemini_client.chat.completions.create(
                    model="gemini-2.0-flash",
                    messages=messages,
                    tools=[_FINDING_TOOL],
                    tool_choice={"type": "function", "function": {"name": "report_findings"}},
                    temperature=0.0,
                )
                return _parse_tool_response(response, file_diff.filename)
            except Exception as e:
                logger.warning("Gemini API failed for %s: %s, falling back to OpenRouter", file_diff.filename, e)

        # Fallback to Groq
        if self._groq_client:
            try:
                response = await self._groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    tools=[_FINDING_TOOL],
                    tool_choice={"type": "function", "function": {"name": "report_findings"}},
                    temperature=0.0,
                )
                return _parse_tool_response(response, file_diff.filename)
            except Exception as e:
                logger.error("Groq API fallback failed for %s: %s", file_diff.filename, e)
                
        return []


def _format_diff_for_llm(file_diff: FileDiff) -> str:
    """Format a file diff for LLM consumption, respecting context limits."""
    parts: list[str] = []
    total_lines = 0
    for hunk in file_diff.hunks:
        if total_lines > _MAX_HUNK_LINES_FOR_LLM:
            parts.append(f"[... {len(file_diff.hunks)} hunks total, truncated for length ...]")
            break
        parts.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@ {hunk.header}")
        for line in hunk.lines:
            parts.append(line)
            total_lines += 1
    return "\n".join(parts)


def _parse_tool_response(response: Any, filename: str) -> list[Finding]:
    """Extract findings from the OpenAI-compatible tool-use response."""
    findings: list[Finding] = []
    try:
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return []
            
        for tool_call in tool_calls:
            if tool_call.function.name == "report_findings":
                args = json.loads(tool_call.function.arguments)
                raw_findings = args.get("findings", [])
                
                for rf in raw_findings:
                    try:
                        findings.append(
                            Finding(
                                file=rf.get("file", filename),
                                line_start=rf["line_start"],
                                line_end=rf["line_end"],
                                severity=Severity(rf["severity"]),
                                category=Category(rf["category"]),
                                explanation=rf["explanation"],
                                suggested_fix=rf.get("suggested_fix", ""),
                                source="llm",
                            )
                        )
                    except (KeyError, ValueError) as e:
                        logger.warning("Skipping malformed LLM finding: %s", e)
    except Exception as e:
        logger.warning("Error parsing tool response: %s", e)
        
    return findings


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    """Remove duplicate findings covering the same lines with the same category.
    Prefer rule-based findings over LLM findings when they overlap."""
    seen: set[tuple[str, int, int, str]] = set()
    deduped: list[Finding] = []
    # process rule findings first so they take priority
    sorted_findings = sorted(findings, key=lambda f: (0 if f.source == "rule" else 1))
    for f in sorted_findings:
        key = (f.file, f.line_start, f.line_end, f.category.value)
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    return deduped


def _severity_sort_key(finding: Finding) -> int:
    order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
    return order.get(finding.severity, 4)
