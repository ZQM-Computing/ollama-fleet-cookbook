"""
rag_minimal.py -- a minimal, dependency-light RAG reference implementation
against a local Ollama server.

Pipeline: chunk text files -> embed with Ollama (/api/embeddings) -> store
vectors in a single .npz file -> at query time, rank chunks by cosine
similarity and answer with the top chunks as context (/api/chat).

Dependencies: Python 3.11+ and numpy. HTTP is stdlib urllib -- no SDK.

Usage:
    python rag_minimal.py ingest ./docs --index fleet_docs.npz
    python rag_minimal.py ask "How do I replace an OSD?" --index fleet_docs.npz
    python rag_minimal.py --self-test        # no server needed; fake embedder

Environment:
    OLLAMA_HOST   default http://localhost:11434
    EMBED_MODEL   default nomic-embed-text
    CHAT_MODEL    default llama3.1:8b

Design notes (the pattern, in one paragraph): the index is a file, not a
service -- for a personal/small-team corpus that fits in memory, a service-
grade vector database is operational debt you don't need yet. The upgrade
path (sqlite-vec, pgvector, a real vector DB) starts exactly when the .npz
file stops fitting comfortably in RAM or multiple writers appear; see
docs/rag-architecture.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.1:8b")

CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200


# ---------------------------------------------------------------------------
# Text handling
# ---------------------------------------------------------------------------


def chunk_text(
    text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Split text into overlapping, paragraph-aware chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # Long single paragraph: hard-split with overlap.
            while len(para) > size:
                chunks.append(para[:size])
                para = para[size - overlap :]
            current = para
    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# Embeddings: real (Ollama) and fake (self-test)
# ---------------------------------------------------------------------------


def embed_ollama(texts: list[str]) -> np.ndarray:
    vectors = []
    for text in texts:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "prompt": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read())
        vectors.append(payload["embedding"])
    return np.array(vectors, dtype=np.float32)


def embed_fake(texts: list[str]) -> np.ndarray:
    """Deterministic bag-of-words hashing embedder for --self-test.

    Not semantically meaningful -- just stable enough to exercise chunking,
    ranking, and index I/O without a server."""
    dim = 256
    out = np.zeros((len(texts), dim), dtype=np.float32)
    for i, text in enumerate(texts):
        for token in text.lower().split():
            out[i, int(hashlib.md5(token.encode()).hexdigest(), 16) % dim] += 1.0
    return out


def cosine_rank(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Indices of matrix rows sorted by cosine similarity to query_vec."""
    q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    m = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    return np.argsort(-(m @ q))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_ingest(args: argparse.Namespace, embedder) -> int:
    source = Path(args.source)
    files = (
        sorted(source.rglob("*.md")) + sorted(source.rglob("*.txt"))
        if source.is_dir()
        else [source]
    )
    chunks: list[str] = []
    origins: list[str] = []
    for path in files:
        for chunk in chunk_text(path.read_text(encoding="utf-8", errors="replace")):
            chunks.append(chunk)
            origins.append(str(path))
    if not chunks:
        print("No text chunks found.", file=sys.stderr)
        return 1
    vectors = embedder(chunks)
    np.savez_compressed(
        args.index, vectors=vectors, chunks=np.array(chunks), origins=np.array(origins)
    )
    print(f"Indexed {len(chunks)} chunks from {len(files)} file(s) -> {args.index}")
    return 0


def cmd_ask(args: argparse.Namespace, embedder) -> int:
    data = np.load(args.index, allow_pickle=False)
    vectors, chunks = data["vectors"], [str(c) for c in data["chunks"]]
    query_vec = embedder([args.question])[0]
    top = cosine_rank(query_vec, vectors)[: args.k]
    context = "\n\n---\n\n".join(chunks[i] for i in top)
    print("Context chunks:", [int(i) for i in top])
    if args.no_chat:
        print(context)
        return 0
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(
            {
                "model": CHAT_MODEL,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": "Answer using only the provided context. If the context does not contain the answer, say so plainly.",
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {args.question}",
                    },
                ],
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read())
    print(payload["message"]["content"])
    return 0


def self_test() -> int:
    """Exercise chunking, ranking, and index I/O with the fake embedder."""
    sample = (
        "Ceph OSD replacement starts with marking the OSD out and watching recovery.\n\n"
        "Backups are verified by restoring a guest to an isolated network monthly.\n\n"
        "Proxmox templates are built from vendor cloud images with cloud-init.\n\n"
        "The fleet health script exits nonzero unless every host answers."
    )
    chunks = chunk_text(sample, size=120, overlap=20)
    assert len(chunks) >= 3, f"expected >=3 chunks, got {len(chunks)}"
    vectors = embed_fake(chunks)
    assert vectors.shape == (len(chunks), 256)
    query = embed_fake(["how do I replace a failed OSD in ceph"])[0]
    best = int(cosine_rank(query, vectors)[0])
    assert "OSD replacement" in chunks[best], (
        f"ranking failed: best chunk was {chunks[best]!r}"
    )
    # Index round-trip. Use a temporary directory so the check works on any
    # platform (no hardcoded /tmp) and the handle is released before cleanup.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir) / "rag_minimal_selftest.npz"
        np.savez_compressed(
            tmp,
            vectors=vectors,
            chunks=np.array(chunks),
            origins=np.array(["t"] * len(chunks)),
        )
        with np.load(tmp, allow_pickle=False) as back:
            assert back["vectors"].shape == vectors.shape
    print(
        f"self-test OK: {len(chunks)} chunks, ranking picked the OSD chunk, index round-trips"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--self-test", action="store_true", help="run the offline self-test and exit"
    )
    sub = parser.add_subparsers(dest="command")
    p_in = sub.add_parser(
        "ingest", help="chunk + embed a file or directory into an index"
    )
    p_in.add_argument("source")
    p_in.add_argument("--index", default="rag_index.npz")
    p_ask = sub.add_parser("ask", help="answer a question from an index")
    p_ask.add_argument("question")
    p_ask.add_argument("--index", default="rag_index.npz")
    p_ask.add_argument("-k", type=int, default=4)
    p_ask.add_argument(
        "--no-chat", action="store_true", help="print ranked context only"
    )
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.command == "ingest":
        return cmd_ingest(args, embed_ollama)
    if args.command == "ask":
        return cmd_ask(args, embed_ollama)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
