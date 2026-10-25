# ollama-fleet-cookbook — Ollama Fleet Cookbook for Local LLM Operations

<!-- ZQM-START -->
<!-- markdownlint-disable MD033 -->
<p align="center">
  <strong>ZQM Computing — Geospatial Engineering & Scientific Computing</strong><br>
  <a href="https://github.com/ZQM-Computing">ZQM Computing</a> •
  <a href="https://github.com/ZQM-Labs">ZQM Labs</a>
</p>
<!-- markdownlint-enable MD033 -->
<!-- ZQM-END -->

[![Validate](https://github.com/ZQM-Computing/ollama-fleet-cookbook/actions/workflows/validate.yml/badge.svg)](https://github.com/ZQM-Computing/ollama-fleet-cookbook/actions/workflows/validate.yml)

A cookbook for **self-hosted local language models with Ollama**, from a single machine to a small multi-node fleet. It covers fleet health checks, manifest-driven model management, request distribution, VRAM budgeting, operational runbooks, and a minimal retrieval-augmented generation (RAG) reference in dependency-light Python. These are reusable patterns, not the live fleet's configuration; verify model licenses, hardware capacity, network exposure, and authentication before deployment.

## Repository role and status

**Status:** Active, public.

**What this repository is:** Ollama fleet operations patterns — manifest-driven model management, fleet health checks, load-spreading topologies, VRAM budgeting, operations runbooks, and a minimal RAG reference implementation, generalized from production self-hosted operations. This is a pattern library, not the live fleet's configuration.

**What it contributes:** Part of the ZQM Computing public pattern portfolio — production-grade pattern and reference repositories that document engineering practice across the stack. This repository is the reusable pattern library for its layer: working code and runbooks that practitioners can lift into their own pipelines, and portfolio evidence of the engineering practice behind ZQM Computing. The umbrella index for the series is [geospatial-cookbooks](https://github.com/ZQM-Computing/geospatial-cookbooks).

**Standing:** This repository is maintained independently. Automated checks cover only the paths and environments configured in its workflows; they do not establish production readiness or operational certification. This repository is standalone — no other repository or deployment depends on it.

## What's inside

**Scripts** ([`scripts/`](scripts/))

| Script | What it does |
|---|---|
| `fleet_health.sh` | Per-host API check (`/api/tags`, `/api/ps`): installed vs. loaded models; exits nonzero if any host is down |
| `model_sync.sh` | Converges every host to a model manifest (pinned names in [`examples/models.txt`](examples/models.txt)) via the Ollama pull API |

**Reference implementation** ([`python/rag_minimal.py`](python/rag_minimal.py))

A complete RAG pipeline in one file — paragraph-aware chunking, embeddings via Ollama, a single-file `.npz` vector index, cosine ranking, and grounded chat answers — using only Python + numpy. Includes an offline `--self-test` mode (no server needed) that CI runs on every push.

**Docs** ([`docs/`](docs/))

| Doc | Covers |
|---|---|
| [Fleet topology](docs/fleet-topology.md) | One node done well → uniform fleet behind a proxy → role-shaped fleets; the model-locality and cold-start caveats; VRAM budgeting |
| [Model management](docs/model-management.md) | Manifests as source of truth, pinned tags, digest discipline, deliberate upgrades, disk hygiene |
| [RAG architecture](docs/rag-architecture.md) | When the file-simple design is right, the graduation ladder (sqlite-vec → pgvector → vector DB), chunking and grounding discipline |
| [Operations](docs/operations.md) | The daily three checks, common-failure first moves, upgrade soaking, observability without a platform team |

## Quick start

```bash
# Health of the default local node (or pass hosts / set OLLAMA_FLEET_HOSTS)
./scripts/fleet_health.sh gpu-box:11434 chat-node:11434

# Index a docs folder and ask it questions (needs a local Ollama)
pip install numpy
python python/rag_minimal.py ingest ./docs --index fleet_docs.npz
python python/rag_minimal.py ask "How do I replace an OSD?" --index fleet_docs.npz

# No server handy? The pipeline still proves itself:
python python/rag_minimal.py --self-test
```

## Usage

Start with the [Quick start](#quick-start) to bring up a node, then apply
the configurations and patterns here to grow and operate the fleet —
adapt the hostnames, models, and service settings to your own hardware.

## Who this is for

Developers and homelab/infrastructure folks who have Ollama running on one machine and are hitting the next set of questions — a second GPU box, teammates as users, models drifting between hosts, a RAG prototype that needs to become a habit. Also teams evaluating local inference for privacy or cost reasons who want the operational shape before committing hardware.

## Design principles

1. **Uniformity beats cleverness.** Fleets fail by drift — models, versions, configs. Manifests and health checks exist to make drift visible and convergence boring.
2. **The network is the security model.** Ollama serves an unauthenticated API; these patterns assume LAN/VPN placement and say so wherever it matters.
3. **Start file-simple.** The RAG reference is one file and one index file on purpose; the docs name the measured pressures that justify each step up in infrastructure.
4. **Verify with the real thing.** The health script checks hosts directly (never through the proxy that might mask them), and the RAG pipeline ships a self-test that exercises chunking, ranking, and index I/O.

## Repository layout

```text
.
├── scripts/    # fleet health + model manifest sync (bash, curl, jq)
├── python/     # rag_minimal.py — the RAG reference implementation
├── docs/       # topology, model management, RAG architecture, operations
├── examples/   # a starter model manifest
└── .github/    # CI: bash -n, py_compile, RAG self-test
```

## Contributing

Fleet scars welcome: failure modes, version-specific behaviors, topology lessons. See [`CONTRIBUTING.md`](CONTRIBUTING.md). Keep examples free of real hostnames, addresses, and anything from a private deployment.

## Maintainer

Maintained by [ZQM Computing](https://github.com/ZQM-Computing). Patterns generalized from operating a self-hosted Ollama fleet and local-AI tooling in production by Alex Zelenski, GISP.

## Related repositories

- [postgis-cookbook](https://github.com/ZQM-Computing/postgis-cookbook) — PostGIS SQL examples: spatial indexing, joins & KNN, SRID management, vector tiles, data quality, partitioning
- [duckdb-spatial-cookbook](https://github.com/ZQM-Computing/duckdb-spatial-cookbook) — DuckDB Spatial patterns for analytical geospatial SQL: GeoParquet, spatial joins, KNN, H3 aggregation — no server required
- [pgrouting-cookbook](https://github.com/ZQM-Computing/pgrouting-cookbook) — pgRouting network analysis on PostGIS: shortest path, driving distance, isochrones, turn restrictions, traffic-aware routing
- [geopandas-cookbook](https://github.com/ZQM-Computing/geopandas-cookbook) — GeoPandas/Shapely patterns for Python geospatial workflows: spatial joins, CRS handling, overlays, interpolation, performance
- [gdal-cookbook](https://github.com/ZQM-Computing/gdal-cookbook) — GDAL/OGR command-line patterns: conversion, reprojection, clipping, mosaicking — runnable examples; validate against your GDAL version and target data
- [stac-cookbook](https://github.com/ZQM-Computing/stac-cookbook) — STAC patterns for geospatial data discovery: catalogs, item validation, search API, bulk operations, cloud deployment
- [maplibre-cookbook](https://github.com/ZQM-Computing/maplibre-cookbook) — MapLibre GL JS patterns for frontend vector tile rendering: custom layers, 3D terrain, performance tuning, interactive maps
- [cog-cookbook](https://github.com/ZQM-Computing/cog-cookbook) — Cloud Optimized GeoTIFF patterns: creation, validation, TiTiler serving, xarray integration, performance benchmarking
- [geoparquet-cookbook](https://github.com/ZQM-Computing/geoparquet-cookbook) — GeoParquet patterns for columnar geospatial analytics: partitioning, predicate pushdown, DuckDB/Spark integration
- [h3-cookbook](https://github.com/ZQM-Computing/h3-cookbook) — H3 hexagonal grid patterns: indexing, aggregation, visualization, grid comparisons, performance benchmarks
- [qgis-resources](https://github.com/ZQM-Computing/qgis-resources) — QGIS expressions, PyQGIS snippets, Processing scripts, styles, and QField field-collection guides
- [geospatial-api-reference](https://github.com/ZQM-Computing/geospatial-api-reference) — OGC API – Features reference implementation with FastAPI and PostGIS backends
- [proxmox-ceph-operations](https://github.com/ZQM-Computing/proxmox-ceph-operations) — Proxmox VE + Ceph operations runbooks: health checks, backup discipline, OSD replacement, upgrade checklists
- [geospatial-cookbooks](https://github.com/ZQM-Computing/geospatial-cookbooks) — Umbrella index for all ZQM geospatial pattern repos

## Installation

```bash
pip install -r requirements.txt
```

Requires Python 3.11+.

## License

MIT — see [`LICENSE`](LICENSE).

*Part of [ZQM Computing](https://github.com/ZQM-Computing) — geospatial engineering, scientific computing, and infrastructure patterns; the geospatial arm of [ZQM Labs](https://zqmlabs.com), makers of Z's Quests & Mischief location games.*

<!-- ZQM-FOOTER-START -->
<!-- markdownlint-disable MD033 -->
---

<p align="center">
  <em>Play more. Plan less.</em><br>
  <a href="https://zqmlabs.com">zqmlabs.com</a> •
  <a href="https://github.com/ZQM-Labs">ZQM Labs</a> •
  <a href="https://github.com/ZQM-Computing">ZQM Computing</a>
</p>
<!-- markdownlint-enable MD033 -->
<!-- ZQM-FOOTER-END -->
