# Security policy

## Supported version

Security fixes are applied to the `main` branch. This repository contains patterns, scripts, and a reference implementation; it is not a hosted service.

## Reporting a vulnerability

Email **zqmcomputing@gmail.com** with the subject `ollama-fleet-patterns security` if you find a vulnerability in the scripts or example code, or an example that encourages an unsafe deployment. Please do not open a public issue for a sensitive report.

Include the affected file, the impact you observed, and reproduction steps when available.

## The standing warning

Ollama's API has **no authentication**. Everything in this repository assumes hosts sit on a trusted LAN or VPN. Never expose port 11434 (or a proxy in front of it) to the public internet — that is the single most important security property of any Ollama deployment, and any pattern here that appears to suggest otherwise is a bug worth reporting.
