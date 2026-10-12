# Model management discipline

Models are dependencies. Treat them with the same suspicion as packages: pinned, inventoried, and upgraded on purpose.

## The manifest is the source of truth

Every fleet host's model set is described by a manifest like [`examples/models.txt`](../examples/models.txt) — one model per line, explicit tags. [`scripts/model_sync.sh`](../scripts/model_sync.sh) converges hosts to it. Changes to the fleet's capabilities are manifest diffs: reviewable, reversible, and sized before anyone clicks (a new 14B model × 5 hosts is a real download plan).

- **Pin tags, not vibes.** `llama3.1:8b`, not "the latest llama". Ollama tags move; a fleet where hosts pulled at different times quietly becomes a fleet of different models with the same name.
- **Record digests for anything you evaluate against.** Benchmarks and evals are only comparable when the model bits are identical; `/api/tags` reports digests — capture them with your eval results.

## Upgrade procedure

1. Pull the new model on **one** host.
2. Run your smoke prompts/evals there (even ten fixed questions with eyeball review beats zero).
3. Update the manifest, sync the fleet during a low-use window.
4. Keep the previous version until the new one has survived a week of real use; then remove deliberately (`ollama rm`), not by disk pressure.

## Disk discipline

- Model stores grow monotonically if you let them: every experiment is 4–40 GB that never leaves. A monthly `ollama list` review against the manifest finds the orphans.
- Embedding models are small; chat models are the budget. Vision models justify themselves or go.
- If the model store filesystem fills, Ollama fails mid-pull and can leave partial blobs — free space alerts belong on the model volume specifically, not just the root filesystem.

## Naming for roles

With role-shaped fleets (see [fleet-topology.md](fleet-topology.md)), keep a manifest per role (`models-chat.txt`, `models-embed.txt`) rather than conditionals in one file. Boring files, obvious diffs.
