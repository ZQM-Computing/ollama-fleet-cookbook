# Contributing

## Ground rules

1. **Patterns, not deployments.** Contribute the transferable shape of a solution. Real hostnames, LAN addresses, model-store paths from a live deployment, and anything identifying a private setup stay out.
2. **Scripts are honest about mutation.** Read-only checks must never mutate; the sync script mutates by design and says so in its header. Keep that labeling accurate.
3. **State versions.** Ollama's behavior (memory handling, API fields, defaults) shifts between releases — note the version your contribution was verified on.
4. **The self-test must stay green.** Changes to `python/rag_minimal.py` keep `python/rag_minimal.py --self-test` passing with no server and no network.
5. **Measured claims.** Sizing and performance guidance should say how it was measured or be framed as a rule of thumb, not a benchmark.
