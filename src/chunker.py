"""

Splits source files in a semantically coherent chunk for embedding.
-- WHat that means is that the model creates chunks based of meaning and topic shifts rather than fixed character counts  and token limmits.
----- Sentence Splitting - Vector Embedding (Sentences converted to Vectors) - Similarity Scoring (Chunking based on semantic similarity and topic shifts)


Strategy - AST based function/class level chunking for python, line level fallback with overlap for everything else.

"""

import ast
from dataclasses import dataclass
from pathlib import Path

from src.config import FALLBACK_CHUNK_LINES, FALLBACK_CHUNK_OVERLAP

@dataclass
class Chunk:
    file_path: str
    content: str
    start_line: int
    end_line: int
    symbol: str | None     # function/class name, if known
    kind: str              # "function" | "class" | "window"

def _chunk_python(path: Path, source: str) -> list[Chunk]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _chunk_by_window(path, source)
    lines = source.splitlines()
    chunks = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        body = "\n".join(lines[start:end])
        if not body.strip():
            continue
        chunks.append(Chunk(
            file_path=str(path),
            content=body,
            start_line=node.lineno,
            end_line=end,
            symbol=node.name,
            kind="class" if isinstance(node, ast.ClassDef) else "function",
        ))

    if not chunks:
        return _chunk_by_window(path, source)
    return chunks

def _chunk_by_window(path: Path, source: str) -> list[Chunk]:
    lines = source.splitlines()
    chunks = []
    step = max(1,FALLBACK_CHUNK_LINES - FALLBACK_CHUNK_OVERLAP)

    for start in range(0, len(lines), step):
        window = lines[start:start + FALLBACK_CHUNK_LINES]
        if not any(l.strip() for l in window):
            continue
        chunks.append(Chunk(
            file_path = str(path),
            content = "\n".join(window),
            start_line = start + 1,
            end_line=min(start + FALLBACK_CHUNK_LINES, len(lines)),
            symbol=None,
            kind="window"
        ))
    return chunks

def chunk_file(path: Path)-> list[Chunk]:
    try:
        source=path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    if not source.strip():
        return []
    if path.suffix == ".py":
        return _chunk_python(path, source)
    return _chunk_by_window(path, source)