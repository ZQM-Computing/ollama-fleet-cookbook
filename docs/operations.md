# Operations: keeping a local fleet honest

## The daily three

1. **Fleet answers.** [`scripts/fleet_health.sh`](../scripts/fleet_health.sh) green across hosts — API up, expected models loaded or loadable.
2. **Disk headroom on model stores.** The failure you get from a full model volume (corrupt partial pulls, failed loads) is worse than the alert is annoying.
3. **One real prompt.** Automated checks verify plumbing; a human prompt each morning verifies the thing users feel. Thirty seconds.

## Common failures and first moves

| Symptom | First move |
| --- | --- |
| Requests hang, no error | Check VRAM: a load OOM often presents as a stall. `nvidia-smi` (or the host's GPU tool), then Ollama's logs, then reduce `OLLAMA_NUM_PARALLEL` |
| Model answers garbage after weeks of fine service | Verify the digest (`/api/tags`) — a well-meaning pull may have replaced your pinned model. Re-pull the pinned tag. |
| One host slow, fleet "fine" | Cold model + round-robin: the slow host is loading on the request path. Warm it (`keep_alive`) or align manifests |
| Pull fails midway, model listed but broken | Remove and re-pull the model; partial blobs don't heal |
| Everything down after an OS update | Ollama service unit + GPU driver is the usual pair; check the service first, the driver second, the network third |

## Upgrades

- Upgrade Ollama on one host, soak a day with real traffic, then roll. The API is stable, but runtime behavior (memory, scheduling) shifts between versions.
- Keep a known-good version noted per host before you start — downgrade is just a reinstall away only if you know which version to reinstall.
- Driver and Ollama upgrades are separate changes on separate days. Combining them makes the postmortem a coin flip.

## Observability without a platform team

Ollama's surface is small: the API (`/api/tags`, `/api/ps`), the service log, and host metrics. A cron'd health script with alerting on exit code, a disk check, and a weekly human review of `/api/ps` patterns (which models are *actually* loaded all day — that's your real demand signal for manifest pruning) covers a small fleet completely. Graduate to dashboards when the fleet outgrows the daily three, not before.
