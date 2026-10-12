# RAG architecture: start file-simple, graduate on evidence

The reference implementation in [`python/rag_minimal.py`](../python/rag_minimal.py) is deliberately unambitious: chunk → embed via Ollama → one `.npz` index file → cosine rank → chat with context. That shape is *correct* for a large class of real problems, and the discipline is knowing exactly which pressure should change it.

## When the minimal shape is right

- Corpus is documents a person could enumerate (runbooks, notes, manuals, a project's docs): thousands of chunks, not millions.
- One writer (ingest is a batch job), many readers.
- Query latency budget is conversational, and the embedding model is local — the .npz loads in well under a second at this scale.

## The graduation ladder

| Pressure you can measure | Move |
|---|---|
| Index file takes > a few seconds to load / RAM pinches | sqlite-vec in a single file DB — same operational shape, real indexing |
| Multiple services must query/update concurrently | pgvector on the Postgres you already run, or a dedicated vector DB (Qdrant/Chroma) |
| Recall quality disappoints on real questions | Before touching infrastructure: better chunking (structure-aware), a stronger embedding model, hybrid BM25 + vector ranking, reranking. Infrastructure is rarely the recall problem. |
| Corpus churn is continuous (tickets, chats) | Streaming ingest pipeline; the batch reindex becomes the bottleneck, not the store |

## Chunking notes (where RAG quality is actually decided)

- Chunk on *structure* first (headings, paragraphs), size second. The reference splitter is paragraph-aware with overlap for exactly this reason.
- Overlap is insurance against answers split across boundaries; 10–20% is the usual band.
- Keep provenance with every chunk (the reference stores the source path) — an answer that can't cite its source is a rumor.
- Evaluate with real questions from real users of the corpus. Synthetic eval sets measure how well the system answers questions nobody asks.

## Grounding contract

The reference prompt instructs the model to answer only from context and to say so when the context is insufficient. Keep that contract in every scaled-up version: most "the RAG hallucinated" incidents are a prompt that invited improvisation, on top of retrieval that returned mush. Fix retrieval first, keep the contract always.
