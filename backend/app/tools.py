"""
Agent tool definitions.

Each tool is a callable with a typed schema that the LLM can invoke.
Tools handle sandboxing, timeouts, and output truncation internally.
"""
from __future__ import annotations

import ast
import json
import logging
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas — these are the OpenAI function-calling definitions the agent
# sees and can invoke during its ReAct loop.
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_linter",
            "description": (
                "Run a Python linter (ruff) on the given code snippet. "
                "Returns linter warnings/errors. Use this to check for style "
                "violations, unused imports, or basic code quality issues."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python source code to lint.",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Original filename (for context in linter output).",
                    },
                },
                "required": ["code", "filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": (
                "Execute a Python test snippet in a sandboxed environment. "
                "Returns stdout/stderr. Use this when you suspect a logic bug "
                "and want to verify with a quick test."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "test_code": {
                        "type": "string",
                        "description": "Python test code to execute (should be self-contained).",
                    },
                },
                "required": ["test_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_codebase",
            "description": (
                "Search the repository codebase for relevant code snippets using "
                "semantic search. Returns the most relevant code chunks. Use this "
                "when you need to understand how a function is used elsewhere, or "
                "to find related implementations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query describing what you're looking for.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 3).",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dependencies",
            "description": (
                "Analyze the import/dependency graph for a Python file. "
                "Returns a list of imports and what they resolve to. "
                "Use this to understand the blast radius of a change."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python source code to analyze imports for.",
                    },
                    "filename": {
                        "type": "string",
                        "description": "The filename being analyzed.",
                    },
                },
                "required": ["code", "filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_blame",
            "description": (
                "Look up the last modification history for specific lines in a file. "
                "Returns who changed the code and when. Use this to assess whether "
                "a pattern is intentional or accidental."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The file to look up blame information for.",
                    },
                    "line_start": {
                        "type": "integer",
                        "description": "Start line number.",
                    },
                    "line_end": {
                        "type": "integer",
                        "description": "End line number.",
                    },
                },
                "required": ["filename", "line_start", "line_end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_review",
            "description": (
                "Submit your final code review findings. Call this when you have "
                "completed your analysis and are ready to report. If no issues "
                "were found, submit an empty findings list."
            ),
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
                                "confidence": {
                                    "type": "number",
                                    "description": "Confidence score 0.0-1.0. Only findings >= threshold are kept.",
                                },
                                "explanation": {"type": "string"},
                                "suggested_fix": {"type": "string"},
                                "reasoning_trace": {
                                    "type": "string",
                                    "description": "Brief summary of what tools/evidence led to this finding.",
                                },
                            },
                            "required": [
                                "file", "line_start", "line_end", "severity",
                                "category", "confidence", "explanation", "suggested_fix",
                            ],
                        },
                    },
                },
                "required": ["findings"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _truncate(text: str, max_bytes: int | None = None) -> str:
    """Truncate output to prevent blowing up the context window."""
    limit = max_bytes or get_settings().SANDBOX_MAX_OUTPUT_BYTES
    if len(text.encode("utf-8", errors="replace")) > limit:
        truncated = text.encode("utf-8", errors="replace")[:limit].decode("utf-8", errors="replace")
        return truncated + "\n... [output truncated]"
    return text


def _safe_subprocess(cmd: list[str], cwd: str | None = None, input_text: str | None = None) -> str:
    """Run a subprocess with timeout and output limits. Returns stdout+stderr."""
    settings = get_settings()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.SANDBOX_TIMEOUT_SECONDS,
            cwd=cwd,
            input=input_text,
            # SECURITY: Don't inherit env vars that might contain secrets
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/usr/local/bin"),
                "HOME": tempfile.gettempdir(),
                "LANG": "en_US.UTF-8",
            },
        )
        output = result.stdout + result.stderr
        return _truncate(output)
    except subprocess.TimeoutExpired:
        return f"[ERROR] Command timed out after {settings.SANDBOX_TIMEOUT_SECONDS}s"
    except FileNotFoundError as e:
        return f"[ERROR] Command not found: {e}"
    except Exception as e:
        return f"[ERROR] Subprocess failed: {e}"


def tool_run_linter(code: str, filename: str) -> str:
    """Run ruff linter on a code snippet in a temp file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / filename
        filepath.write_text(code, encoding="utf-8")
        output = _safe_subprocess(
            ["python", "-m", "ruff", "check", "--select", "ALL", "--no-fix", str(filepath)],
            cwd=tmpdir,
        )
        if not output.strip():
            return "No linter issues found."
        # Strip absolute paths from output for cleanliness
        return output.replace(str(tmpdir) + os.sep, "")


def tool_run_tests(test_code: str) -> str:
    """Execute a test snippet in a sandboxed temp directory."""
    # SECURITY: Sanitize — reject code that imports os.system, subprocess, etc.
    dangerous_patterns = ["os.system", "subprocess", "shutil.rmtree", "open(", "__import__"]
    for pattern in dangerous_patterns:
        if pattern in test_code:
            return f"[BLOCKED] Test code contains potentially dangerous pattern: {pattern}"

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_agent.py"
        test_file.write_text(test_code, encoding="utf-8")
        return _safe_subprocess(
            ["python", "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header"],
            cwd=tmpdir,
        )


def tool_search_codebase(query: str, top_k: int = 3) -> str:
    """Search the vector store for relevant code. Returns formatted results."""
    try:
        from app.retrieval import search_index
        results = search_index(query, top_k=top_k)
        if not results:
            return "No relevant code found in the index."
        parts = []
        for i, r in enumerate(results, 1):
            parts.append(f"--- Result {i} (score: {r['score']:.3f}) ---")
            parts.append(f"File: {r['file']}")
            parts.append(r["content"])
        return "\n".join(parts)
    except Exception as e:
        logger.warning("Codebase search failed: %s", e)
        return f"[ERROR] Search unavailable: {e}"


def tool_get_dependencies(code: str, filename: str) -> str:
    """Parse imports from Python source code using AST."""
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as e:
        return f"[ERROR] Could not parse {filename}: {e}"

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"from {module} import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))

    if not imports:
        return f"No imports found in {filename}."

    return f"Dependencies for {filename}:\n" + "\n".join(f"  - {imp}" for imp in imports)


def tool_git_blame(filename: str, line_start: int, line_end: int) -> str:
    """
    Simulate git blame for a file region.
    In production, this would call `git blame -L start,end filename` on the
    cloned repo. For now, returns a descriptive message since we work with
    diffs, not full repos.
    """
    # ASSUMPTION: We don't clone the full repo. In production, the webhook
    # handler would clone to a temp dir and this tool would run real git blame.
    return (
        f"[git blame] {filename} lines {line_start}-{line_end}: "
        f"Blame data unavailable — PR diff mode. In production, this would "
        f"show author/date/commit for each line."
    )


# ---------------------------------------------------------------------------
# Tool dispatcher — maps tool name → implementation
# ---------------------------------------------------------------------------

TOOL_DISPATCH: dict[str, callable] = {
    "run_linter": lambda args: tool_run_linter(args["code"], args["filename"]),
    "run_tests": lambda args: tool_run_tests(args["test_code"]),
    "search_codebase": lambda args: tool_search_codebase(args["query"], args.get("top_k", 3)),
    "get_dependencies": lambda args: tool_get_dependencies(args["code"], args["filename"]),
    "git_blame": lambda args: tool_git_blame(args["filename"], args["line_start"], args["line_end"]),
    # submit_review is handled specially by the agent loop — not dispatched here
}
