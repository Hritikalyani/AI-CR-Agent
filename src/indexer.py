"""
Builds and queries the vector index over a repository
"""

import hashlib
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from src.chunker import Chunk, chunk_file
from src.config import (CHROMA_COLLECTION, CHROMA_PERSIST_DIR, EMBEDDING_MODEL, RETRIEVAL_TOP_K, SCANNABLE_EXTENSIONS, SKIP_DIRS)

_model = None
_collection = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer (EMBEDDING_MODEL)
    return _model

def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection =client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection

def _chunk_id(chunk: Chunk) -> str:
    raw = f"{chunk.file_path}:{chunk.start_line}:{chunk.end_line}"
    return hashlib.sha1(raw.encode()). hexdigest()

def build_index(repo_path: str, verbose: bool = True) -> int:
    import os
    collection = _get_collection()
    model = _get_model()

    files = []

    root = Path(repo_path).resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if Path(f).suffix in SCANNABLE_EXTENSIONS:
                files.append(Path(dirpath) / f)

    all_chunks = []

    for f in files:
        all_chunks.extend(chunk_file(f))

    if not all_chunks:
        return 0

    texts = [c.content for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=verbose, batch_size=32).tolist()
    collection.upsert(
        ids = [_chunk_id(c) for c in all_chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{
            "file_path": c.file_path,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "symbol": c.symbol or "",
            "kind": c.kind,
        } for c in all_chunks]
    )

    return len(all_chunks)

def retrieve_related(query_text: str, exclude_file: str | None = None, k: int = RETRIEVAL_TOP_K) -> list[dict]:
    collection = _get_collection()
    model = _get_model()

    query_emb = model.encode([query_text]).tolist()

    results = collection.query(query_embeddings=query_emb, n_results=k * 3)

    out = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]):
        if exclude_file and meta["file_path"] == exclude_file:
            continue
        out.append({"content": doc, "meta": meta, "distance": dist})
        if len(out) >= k:
            break

    return out