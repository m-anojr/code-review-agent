# Agentic AI Code Review System — Architecture

## Overview

The system upgrades from a single-shot LLM call to an **agentic loop** where the
agent plans its own investigation, calls tools (linters, test runners, git blame,
dependency graph, AST search), retrieves relevant context from a vector store,
and only produces a verdict once it has gathered enough evidence. Deterministic
rules run as a **pre-filter** — high-confidence, zero-cost findings that the
agent does not need to re-discover.

## Pipeline

```
GitHub Webhook (PR event)
        │
        ▼
  ┌─────────────────────┐
  │  Webhook Handler    │  Validates signature, extracts owner/repo/pr
  │  (FastAPI)          │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │  Retrieval Layer    │  1. Fetch PR diff via GitHub API
  │                     │  2. AST-chunk changed files + surrounding context
  │                     │  3. Query vector store for related code, past PR
  │                     │     comments, style guide snippets
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │  Pre-Filter:        │  Run deterministic rules (secrets, SQLi, exceptions)
  │  Deterministic      │  These findings are final — they skip the agent loop.
  │  Rules              │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────┐
  │  Agent Orchestration Loop (ReAct-style)      │
  │                                              │
  │  1. PLAN: Given the diff + retrieved context │
  │     + rule findings, decide what to check    │
  │  2. ACT: Call a tool (linter, test runner,   │
  │     git blame, AST search, dep graph)        │
  │  3. OBSERVE: Incorporate tool result         │
  │  4. Repeat until confident or budget hit     │
  │  5. SYNTHESIZE: Produce structured findings  │
  └────────┬────────────────────────────────────┘
           │
           ▼
  ┌─────────────────────┐
  │  Confidence Filter  │  Drop findings below threshold (precision-first)
  │  + Deduplication    │  Merge with rule findings, deduplicate
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │  Output Formatter   │  Post inline PR comments via GitHub API
  │  + GitHub Poster    │  OR return via REST API to the UI
  └─────────────────────┘
```

## Agent Loop Design

The agent uses a **ReAct** (Reason + Act) loop:
- **Max iterations**: 5 (configurable). Prevents runaway token spend.
- **Token budget**: 32k tokens per PR (configurable). Tracked per-call.
- **Completion signal**: The agent calls a `submit_review` tool when it's done,
  or the loop ends when max iterations / budget is hit.
- **Tool choice**: The LLM decides which tool to call based on the diff content.
  E.g., if it sees a function call, it may check the dependency graph; if it
  sees a SQL query, it may skip (already caught by rules).

## Tool Interfaces

| Tool | Description | When Used |
|------|-------------|-----------|
| `run_linter` | Run Ruff/flake8 on changed files | Always, first iteration |
| `run_tests` | Execute pytest in sandboxed container | When agent suspects logic bug |
| `git_blame` | Show who last changed a code region | When assessing intent/history |
| `search_codebase` | AST-aware search in repo context | When agent needs surrounding code |
| `get_dependencies` | Show import graph for a file | When checking impact of changes |
| `submit_review` | Finalize and output findings | Agent calls when done |

## Retrieval Layer

- **Chunking**: AST-aware — split by function/class/module boundaries, not
  fixed character windows. Falls back to line-based chunking for non-Python.
- **Embedding**: `text-embedding-3-small` via OpenAI-compatible API (Groq doesn't
  serve embeddings, so we use a local sentence-transformers model as default).
- **Vector store**: ChromaDB (embedded, file-based). Zero infrastructure.
  Re-indexes on each PR by diffing the changed file list.
- **Sources indexed**: Changed files' full context, past review findings from
  the SQLite DB, and any `.md` style guide files in the repo root.

## Output Schema

```json
{
  "file": "src/auth.py",
  "line_start": 42,
  "line_end": 45,
  "severity": "high",
  "category": "security",
  "confidence": 0.92,
  "explanation": "Password comparison uses `==` instead of constant-time comparison.",
  "suggested_fix": "Use `hmac.compare_digest()` or `secrets.compare_digest()`.",
  "source": "agent",
  "tools_used": ["search_codebase", "get_dependencies"],
  "reasoning_trace": "Checked if any wrapper exists — none found."
}
```

## Key Design Decisions

1. **Deterministic rules as pre-filter, not agent tool**: Rules are fast, free,
   and 100% precision. Running them before the agent saves tokens and avoids the
   LLM second-guessing known-good detections.
2. **Precision > Recall**: Confidence threshold defaults to 0.7. Better to miss
   a style nit than post a false positive that erodes developer trust.
3. **ChromaDB over Pinecone/Weaviate**: Zero infrastructure, embedded mode,
   sufficient for single-repo analysis. ASSUMPTION: Single-repo, not multi-tenant.
4. **Groq as primary LLM**: Free tier, fastest inference, good tool-use support.
   Gemini as fallback. ASSUMPTION: Small team, cost-sensitive.
5. **Sandboxed execution via subprocess + tempdir**: No Docker-in-Docker needed
   for linting. Test execution uses isolated temp directories with timeouts.
