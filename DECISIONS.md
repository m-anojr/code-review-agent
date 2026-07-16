# Design Decisions

## Hybrid Rules + LLM Architecture
We use deterministic rules (regex/AST-based) for certain classes of issues like hardcoded secrets, simple SQL injection, and bare except clauses.
- **Why**: LLMs are expensive and can hallucinate. Static rules are fast, zero-cost, and have 100% precision for known patterns. The LLM is reserved for logic bugs, race conditions, and complex state issues that static analysis tools miss. The LLM is provided with the static rule findings in its prompt to avoid duplicating effort.

## Structured LLM Output
We enforce a strict JSON schema via OpenAI function calling (using the `report_findings` tool format) for the LLM output.
- **Why**: Parsing unstructured Markdown code reviews is brittle. Function calling ensures the LLM returns findings with a specific file, line range, severity enum, and category enum, making it trivial to map back to the unified diff for inline display.

## API Fallback Mechanism
The analysis engine attempts to use Gemini 1.5 Flash first, and falls back to OpenRouter if the first call fails.
- **Why**: Ensures high availability and leverages free-tier API limits across multiple providers.

## SQLite Storage
We use SQLite (`aiosqlite`) to persist review history and diffs.
- **Why**: At this scale, Postgres is overkill. SQLite requires zero configuration, ships as a single file, and perfectly handles the concurrency needs of an internal developer tool.

## Dry-Run Default
The GitHub client has a `post_review_comment` method, but it is not exposed via the primary API flow.
- **Why**: Posting comments requires write access to the repository. By default, the tool only reads the diff and stores the findings locally. This prevents the agent from spamming real repositories while still proving the analysis capability.
