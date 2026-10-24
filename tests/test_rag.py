"""Tests for the ollama-fleet-cookbook RAG reference (python/rag_minimal.py).

These tests package the offline checks already proven by
``python rag_minimal.py --self-test`` (chunking, ranking, index round-trip)
as pytest, so they run in CI instead of only as a standalone self-test.
They need no Ollama server: they use the deterministic ``embed_fake``
embedder from the module itself. The live-server paths (``embed_ollama``,
``cmd_ask`` with chat) are deliberately not tested here.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

import rag_minimal


def test_chunking_paragraph_aware():
    """Short paragraphs that fit are joined, not split mid-paragraph."""
    chunks = rag_minimal.chunk_text("first paragraph\n\nsecond paragraph", size=100)
    assert chunks == ["first paragraph\n\nsecond paragraph"]


def test_chunking_long_paragraph_hard_split_with_overlap():
    """A single over-long paragraph is hard-split, keeping the overlap."""
    text = "a" * 250
    chunks = rag_minimal.chunk_text(text, size=100, overlap=20)
    assert all(len(c) <= 100 for c in chunks)
    assert len(chunks) == 3
    # Second chunk starts 80 chars in, i.e. it overlaps the first by 20.
    assert chunks[1] == "a" * 100
    assert chunks[2] == "a" * 90


def test_embed_fake_deterministic_and_shaped():
    """The fake embedder is stable and returns (n, 256) float32."""
    texts = ["ceph osd replacement", "backup verification"]
    first = rag_minimal.embed_fake(texts)
    second = rag_minimal.embed_fake(texts)
    assert first.shape == (2, 256)
    assert first.dtype == np.float32
    assert np.array_equal(first, second)


def test_cosine_rank_picks_relevant_chunk():
    """Ranking puts the OSD chunk first for an OSD question."""
    chunks = [
        "Ceph OSD replacement starts with marking the OSD out and watching recovery.",
        "Backups are verified by restoring a guest to an isolated network monthly.",
        "Proxmox templates are built from vendor cloud images with cloud-init.",
    ]
    vectors = rag_minimal.embed_fake(chunks)
    query = rag_minimal.embed_fake(["how do I replace a failed OSD in ceph"])[0]
    best = int(rag_minimal.cosine_rank(query, vectors)[0])
    assert best == 0
    assert "OSD" in chunks[best]


def test_index_round_trip(tmp_path):
    """A saved .npz index reloads with identical vectors and chunks."""
    chunks = ["chunk one", "chunk two"]
    vectors = rag_minimal.embed_fake(chunks)
    index = tmp_path / "test_index.npz"
    np.savez_compressed(
        index,
        vectors=vectors,
        chunks=np.array(chunks),
        origins=np.array(["a", "b"]),
    )
    with np.load(index, allow_pickle=False) as back:
        assert back["vectors"].shape == vectors.shape
        assert np.array_equal(back["vectors"], vectors)
        assert [str(c) for c in back["chunks"]] == chunks


def test_self_test_passes():
    """The module's own offline self-test still passes end to end."""
    assert rag_minimal.self_test() == 0
