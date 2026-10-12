# Fleet topology patterns

Three shapes cover nearly every local-LLM setup worth running. Graduate when the current shape's limit starts hurting, not before.

## Shape 1: One node, done well

A single GPU node running Ollama, clients pointing straight at it (`OLLAMA_HOST=host:11434`). This is the right answer for one user or a small team with bursty use.

- Set `OLLAMA_HOST=0.0.0.0` on the server so the LAN can reach it; know that Ollama has **no authentication** — network position is the security model. Never expose port 11434 to the internet.
- `OLLAMA_NUM_PARALLEL` and `OLLAMA_MAX_LOADED_MODELS` are the two knobs that matter: parallel slots trade VRAM for concurrency; loaded-model caps prevent eviction thrash when clients alternate models.
- Keep the model store on fast local storage. Model loads are disk reads of many GB; a spinning-rust model store makes every cold start a coffee break.

## Shape 2: A small fleet behind one name

Two to five nodes, clients pointed at a lightweight reverse proxy (Caddy/nginx/HAProxy) that round-robins `/api/*`. Ollama is stateless per request, so naive round-robin works — with two caveats that shape the rest of this repo:

1. **Model locality:** a request routed to a host missing the model fails. Either every host carries every model ([`scripts/model_sync.sh`](../scripts/model_sync.sh) exists for this) or the proxy must route by model — prefer uniformity; routing rules rot.
2. **Loaded-model warmth:** round-robin spreads load but also spreads cold starts. For a dominant chat model, consider pinning it warm (`keep_alive` on a scheduled tiny request) on every host.

Health lives outside the proxy: [`scripts/fleet_health.sh`](../scripts/fleet_health.sh) checks hosts directly so a proxy-level success can't mask a dead node.

## Shape 3: Roles, not replicas

At some point the fleet differentiates: an embedding node (small GPU/CPU, always warm, serves every RAG ingest), a chat node (the big VRAM), a vision node (multimodal model), a batch node (overnight summarization that must never contend with interactive use). Clients address roles, not hosts. This is where a naming scheme (`embed.lan`, `chat.lan`) and per-role manifests pay off.

The mistake to avoid is skipping Shape 2's uniformity lesson: role nodes still want manifest-driven models and direct health checks, each per role.

## VRAM budgeting (the only sizing math that matters)

- Weights ≈ parameters × bytes-per-param at the chosen quantization (Q4 ≈ 0.5–0.6 bytes/param effective with overhead; Q8 ≈ 1.0).
- Context is not free: KV cache grows with context length × parallel slots. A 14B Q4 model "fitting" in 12 GB at 2k context may OOM at 32k with 4 parallel slots.
- Leave ~10% headroom. Ollama failing a load under pressure presents as a hung request, not a clean error — headroom is what keeps that rare.
