"""Offline tests for python/rag_minimal.py.

These tests exercise only the parts that need no Ollama server: chunking,
the deterministic fake embedder, cosine ranking, and the ingest/ask
round-trip with the fake embedder. They mirror what
``python rag_minimal.py --self-test`` proves, split into individual cases
so a regression names the broken behavior instead of failing one big
self-test. No test contacts a network service.
"""

import argparse
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import rag_minimal


def test_chunk_text_short_text_is_one_chunk():
    assert rag_minimal.chunk_text("hello world") == ["hello world"]


def test_chunk_text_empty_returns_empty():
    assert rag_minimal.chunk_text("") == []
    assert rag_minimal.chunk_text("  \n\n  ") == []


def test_chunk_text_small_paragraphs_combine():
    chunks = rag_minimal.chunk_text("first para\n\nsecond para", size=120, overlap=20)
    assert chunks == ["first para\n\nsecond para"]


def test_chunk_text_long_paragraph_splits_with_overlap():
    text = "x" * 250
    size, overlap = 100, 20
    chunks = rag_minimal.chunk_text(text, size=size, overlap=overlap)
    assert chunks == [text[0:100], text[80:180], text[160:250]]
    # Each continuation re-opens with the previous chunk's tail.
    assert chunks[1][:overlap] == chunks[0][size - overlap :]
    assert chunks[2][:overlap] == chunks[1][size - overlap :]
    assert "".join(c[: size - overlap] for c in chunks[:-1]) + chunks[-1] == text


def test_embed_fake_is_deterministic_and_shaped():
    texts = ["ceph osd replacement", "proxmox templates"]
    first = rag_minimal.embed_fake(texts)
    second = rag_minimal.embed_fake(texts)
    assert first.shape == (2, 256)
    assert first.dtype == np.float32
    assert np.array_equal(first, second)


def test_embed_fake_distinguishes_texts():
    vectors = rag_minimal.embed_fake(["alpha bravo", "charlie delta"])
    assert not np.array_equal(vectors[0], vectors[1])


def test_cosine_rank_puts_identical_vector_first():
    matrix = rag_minimal.embed_fake(
        ["unrelated words here", "ceph osd replacement guide", "more unrelated words"]
    )
    query = rag_minimal.embed_fake(["ceph osd replacement guide"])[0]
    ranking = rag_minimal.cosine_rank(query, matrix)
    assert int(ranking[0]) == 1
    assert sorted(int(i) for i in ranking) == [0, 1, 2]


def test_cosine_rank_handles_zero_vector_without_nan():
    matrix = rag_minimal.embed_fake(["some text", "other text"])
    ranking = rag_minimal.cosine_rank(np.zeros(256, dtype=np.float32), matrix)
    assert len(ranking) == 2
    assert sorted(int(i) for i in ranking) == [0, 1]


def _ingest_args(source, index):
    return argparse.Namespace(source=str(source), index=str(index))


def _ask_args(question, index):
    return argparse.Namespace(question=question, index=str(index), k=4, no_chat=True)


def test_ingest_and_ask_round_trip_with_fake_embedder():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        corpus = tmp / "corpus"
        corpus.mkdir()
        (corpus / "ceph.md").write_text(
            "Ceph OSD replacement starts with marking the OSD out and "
            "watching recovery.\n\n"
            "Backups are verified by restoring a guest to an isolated "
            "network monthly.\n"
        )
        (corpus / "proxmox.md").write_text(
            "Proxmox templates are built from vendor cloud images with "
            "cloud-init.\n"
        )
        index = tmp / "fleet_docs.npz"
        assert rag_minimal.cmd_ingest(_ingest_args(corpus, index), rag_minimal.embed_fake) == 0
        assert index.is_file()
        with np.load(index, allow_pickle=False) as data:
            assert data["vectors"].shape[1] == 256
            assert len(data["chunks"]) == len(data["origins"]) >= 2
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = rag_minimal.cmd_ask(
                _ask_args("how do I replace a failed OSD in ceph", index),
                rag_minimal.embed_fake,
            )
        assert rc == 0
        assert "OSD replacement" in buf.getvalue()


def test_ingest_empty_directory_returns_nonzero():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        empty = tmp / "empty"
        empty.mkdir()
        err = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = err
        try:
            rc = rag_minimal.cmd_ingest(
                _ingest_args(empty, tmp / "out.npz"), rag_minimal.embed_fake
            )
        finally:
            sys.stderr = old_stderr
        assert rc == 1
        assert "No text chunks found." in err.getvalue()


def test_self_test_passes():
    assert rag_minimal.self_test() == 0
