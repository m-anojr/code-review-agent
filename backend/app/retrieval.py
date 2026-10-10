"""Request-scoped AST chunking and code-aware retrieval for changed PR files."""
from __future__ import annotations

import ast
import hashlib
import logging
import math
import re
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AST-aware chunking — splits Python files by function/class boundaries
# ---------------------------------------------------------------------------

def _chunk_python_ast(source: str, filename: str) -> list[dict[str, Any]]:
    """
    Split Python source into semantic chunks based on AST nodes.
    Each chunk is a top-level function or class, with its docstring preserved.
    Falls back to line-based chunking if parsing fails.
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        logger.debug("AST parse failed for %s, falling back to line chunking", filename)
        return _chunk_by_lines(source, filename)

    lines = source.splitlines(keepends=True)
    chunks: list[dict[str, Any]] = []

    # Collect module-level docstring / imports as one chunk
    first_node_line = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first_node_line = node.lineno
            break

    if first_node_line and first_node_line > 1:
        header = "".join(lines[: first_node_line - 1]).strip()
        if header:
            chunks.append({
                "content": header,
                "file": filename,
                "type": "module_header",
                "line_start": 1,
                "line_end": first_node_line - 1,
            })

    # Extract each top-level function/class as a chunk
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end_line = node.end_lineno or node.lineno
            chunk_text = "".join(lines[node.lineno - 1 : end_line]).strip()
            chunks.append({
                "content": chunk_text,
                "file": filename,
                "type": type(node).__name__,
                "line_start": node.lineno,
                "line_end": end_line,
                "name": node.name,
            })

    # If no functions/classes found, treat the whole file as one chunk
    if not chunks:
        return _chunk_by_lines(source, filename)

    return chunks


def _chunk_by_lines(source: str, filename: str, chunk_size: int = 50) -> list[dict[str, Any]]:
    """
    Fallback: split source into fixed-size line chunks.
    Used for non-Python files or files that fail AST parsing.
    """
    lines = source.splitlines()
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk_lines = lines[i : i + chunk_size]
        chunks.append({
            "content": "\n".join(chunk_lines),
            "file": filename,
            "type": "line_chunk",
            "line_start": i + 1,
            "line_end": i + len(chunk_lines),
        })
    return chunks


def chunk_file(source: str, filename: str) -> list[dict[str, Any]]:
    """
    Chunk a source file using the best available strategy.
    Python files get AST-aware chunking; everything else gets line-based.
    """
    if filename.endswith(".py"):
        return _chunk_python_ast(source, filename)
    return _chunk_by_lines(source, filename)


# ---------------------------------------------------------------------------
# Request-scoped changed-file index
# ---------------------------------------------------------------------------

_review_chunks: ContextVar[dict[str, dict[str, Any]] | None] = ContextVar(
    "review_chunks", default=None
)

_CODE_STOPWORDS = {
    "and", "are", "as", "async", "await", "bool", "class", "def", "else",
    "false", "for", "from", "if", "import", "in", "is", "none", "not",
    "or", "pass", "return", "self", "true", "try", "while", "with",
}


@contextmanager
def review_index_scope():
    """Create an isolated, lightweight code index for one PR review."""
    token = _review_chunks.set({})
    try:
        yield
    finally:
        _review_chunks.reset(token)


def index_chunks(chunks: list[dict[str, Any]]) -> int:
    """Add code chunks to the active PR index, deduplicated by content hash."""
    scoped_index = _review_chunks.get()
    if scoped_index is None:
        return 0

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        content = chunk["content"]
        if not content.strip():
            continue
        # Deterministic ID from content hash — same code = same ID = no duplicate
        chunk_id = hashlib.sha256(
            f"{chunk['file']}:{chunk.get('line_start', 0)}:{content}".encode()
        ).hexdigest()[:16]
        ids.append(chunk_id)
        documents.append(content)
        metadatas.append({
            "file": chunk["file"],
            "type": chunk.get("type", "unknown"),
            "line_start": chunk.get("line_start", 0),
            "line_end": chunk.get("line_end", 0),
        })

    if not ids:
        return 0

    for chunk_id, document, metadata in zip(ids, documents, metadatas):
        scoped_index[chunk_id] = {"content": document, **metadata}
    return len(ids)


def index_file(source: str, filename: str) -> int:
    """Chunk and index a single source file. Returns chunks indexed."""
    chunks = chunk_file(source, filename)
    return index_chunks(chunks)


def search_index(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Rank chunks from this PR's changed files with BM25 identifier matching."""
    scoped_index = _review_chunks.get()
    if scoped_index is None:
        return []
    query_terms = _search_terms(query)
    if not query_terms:
        return []

    documents = [
        (item, Counter(_search_term_list(item["content"])))
        for item in scoped_index.values()
    ]
    if not documents:
        return []

    document_frequency = {
        term: sum(term in frequencies for _, frequencies in documents)
        for term in query_terms
    }
    average_length = sum(sum(frequencies.values()) for _, frequencies in documents) / len(documents) or 1
    matches = []
    for item, frequencies in documents:
        length = sum(frequencies.values()) or 1
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            inverse_frequency = math.log(1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            score += inverse_frequency * (frequency * 2.2) / (frequency + 1.2 * (0.25 + 0.75 * length / average_length))
        if score > 0:
            matches.append({
                "content": item["content"],
                "file": item["file"],
                "score": score,
                "line_start": item.get("line_start", 0),
                "line_end": item.get("line_end", 0),
            })
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:max(1, min(top_k, 10))]


def _search_term_list(text: str) -> list[str]:
    """Split code identifiers into normalized tokens for retrieval."""
    terms: list[str] = []
    for identifier in re.findall(r"[A-Za-z][A-Za-z0-9_]*", text):
        parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", identifier).replace("_", " ").split()
        terms.extend(
            part.casefold()
            for part in parts
            if len(part) >= 3 and part.casefold() not in _CODE_STOPWORDS
        )
    return terms


def _search_terms(text: str) -> set[str]:
    return set(_search_term_list(text))
