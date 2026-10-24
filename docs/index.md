# Ollama Fleet Cookbook

Patterns for running **local LLMs with Ollama** as a small fleet instead of
a single box: **fleet health checks**, **manifest-driven model management**,
**load-spreading topologies**, VRAM budgeting, operations runbooks, and a
**minimal RAG reference implementation** in dependency-light Python.

This is the docs-site home page. The README is the full entry point; the
pages below are the detailed guides.

## Guides

- [Fleet topology](fleet-topology.md) — one node done well → uniform fleet
  behind a proxy → role-shaped fleets, with model-locality and cold-start
  caveats and VRAM budgeting.
- [Model management](model-management.md) — manifests as source of truth,
  pinned tags, digest discipline, deliberate upgrades, disk hygiene.
- [RAG architecture](rag-architecture.md) — when the file-simple design is
  right, and the graduation ladder (sqlite-vec → pgvector → vector DB).
- [Operations](operations.md) — the daily three checks, common-failure
  first moves, upgrade soaking, observability without a platform team.

## What's inside

- **Scripts** (`scripts/`): `fleet_health.sh` (per-host API check, exits
  nonzero if any host is down) and `model_sync.sh` (converges hosts to a
  model manifest via the Ollama pull API).
- **Reference implementation** (`python/rag_minimal.py`): chunking,
  embeddings via Ollama, a single-file `.npz` vector index, cosine ranking,
  grounded chat answers — Python + numpy only, with an offline
  `--self-test` mode that needs no server.
- **Examples** (`examples/models.txt`): a starter model manifest with
  pinned versions.

## Tests

`tests/` covers what can be tested offline, and no more:

- `tests/test_rag.py` — chunking, ranking, and index round-trip, packaged
  from the RAG self-test, plus a check that the self-test itself passes.
- `tests/test_fleet_health.py` — mock `curl`/`jq` tests of
  `fleet_health.sh`'s exit-code logic (all hosts up → 0, one host down →
  nonzero with a DOWN report). These do **not** test a real fleet.

Run them with `pip install pytest numpy` then `pytest`. Live-fleet
behaviour is, by design, not covered by automated tests.
