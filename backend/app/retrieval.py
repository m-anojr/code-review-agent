"""
Retrieval layer: AST-aware code chunking and vector search.

Indexes repository code into ChromaDB for semantic retrieval during agent review.
Uses sentence-transformers for local embedding (no API cost).
"""
from __future__ import annotations

import ast
import hashlib
import logging
import re
from pathlib import Path
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
# Vector store — ChromaDB with sentence-transformers embeddings
# ---------------------------------------------------------------------------

_collection = None  # Lazy-initialized ChromaDB collection


def _get_collection():
    """Lazy-initialize the ChromaDB collection with sentence-transformers."""
    global _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.utils import embedding_functions

        from app.config import get_settings
        settings = get_settings()

        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )
        client = chromadb.Client()  # In-memory for simplicity; use PersistentClient for prod
        _collection = client.get_or_create_collection(
            name="codebase",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        return _collection
    except ImportError:
        logger.warning(
            "chromadb or sentence-transformers not installed. "
            "Retrieval will be unavailable. Install with: "
            "pip install chromadb sentence-transformers"
        )
        return None
    except Exception as e:
        logger.warning("Failed to initialize ChromaDB: %s", e)
        return None


def index_chunks(chunks: list[dict[str, Any]]) -> int:
    """
    Add code chunks to the vector store. Returns number of chunks indexed.
    Deduplicates by content hash to avoid re-indexing unchanged code.
    """
    collection = _get_collection()
    if collection is None:
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

    try:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(ids)
    except Exception as e:
        logger.warning("Failed to index chunks: %s", e)
        return 0


def index_file(source: str, filename: str) -> int:
    """Chunk and index a single source file. Returns chunks indexed."""
    chunks = chunk_file(source, filename)
    return index_chunks(chunks)


def index_past_findings(findings: list[dict[str, Any]]) -> int:
    """
    Index past review findings so the agent can learn from history.
    Each finding becomes a searchable document with its explanation.
    """
    chunks = []
    for f in findings:
        content = (
            f"Past finding in {f.get('file', 'unknown')}: "
            f"[{f.get('severity', 'unknown')}] {f.get('category', 'unknown')} — "
            f"{f.get('explanation', '')}"
        )
        chunks.append({
            "content": content,
            "file": f.get("file", "unknown"),
            "type": "past_finding",
            "line_start": f.get("line_start", 0),
            "line_end": f.get("line_end", 0),
        })
    return index_chunks(chunks)


def search_index(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """
    Search the vector store for chunks semantically similar to the query.
    Returns a list of dicts with 'content', 'file', 'score' keys.
    """
    collection = _get_collection()
    if collection is None:
        return []

    try:
        results = collection.query(query_texts=[query], n_results=top_k)
        if not results or not results["documents"]:
            return []

        output = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 1.0
            output.append({
                "content": doc,
                "file": meta.get("file", "unknown"),
                "score": 1.0 - distance,  # Convert distance to similarity
                "line_start": meta.get("line_start", 0),
                "line_end": meta.get("line_end", 0),
            })
        return output
    except Exception as e:
        logger.warning("Search failed: %s", e)
        return []


def clear_index() -> None:
    """Reset the vector store. Useful for re-indexing."""
    global _collection
    _collection = None
