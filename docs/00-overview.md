# Overview

V.I.S.I.O.N. (Virtual Interactive System for Information and Orchestration Networks) is a
Natural Language Operating System / agentic project dashboard: instead of clicking through forms,
users manage Systems (GitHub organizations), Projects (repos), Tasks, and Employees through a
persistent chat/voice HUD, in addition to the normal server-rendered dashboard views.

## Architecture posture

- **Frontend**: Alpine.js (HUD state) + HTMX (server-rendered partial swaps, no client-side
  routing/SPA framework) + the Web Speech API for voice input.
- **Backend**: Flask + SQLAlchemy over a single SQLite database in WAL mode, shared between the
  Flask web process and the background `github-sync` worker for concurrent access.
- **AI Orchestrator**: a local-first LLM router (`orchestrator/`) — Ollama by default, with an
  optional NVIDIA NIM cloud backend and automatic fallback to Ollama on failure. It never talks to
  the database directly; it only ever calls the same `execution/agent_actions.py` functions a
  human or Claude Code would call directly. See `domains/system_architecture.md`.
- **Data flow with GitHub**: strictly one-directional and read-only. See
  `architecture/01-github-readonly-guardrail.md` — this is a hard, non-negotiable limit, not a
  preference.
- **Deployment**: Docker Compose — `web` (Flask/Gunicorn), `github-sync` (background worker),
  `ollama`. See `governance/01-development-workflow.md` for the exact mechanics of editing code
  vs. syncing it into a running container vs. making a change actually take effect.

## Current tech stack

Flask, SQLAlchemy (SQLite/WAL), Alembic migrations, HTMX, Alpine.js, Bootstrap Icons, Ollama
(local LLM), NVIDIA NIM (optional cloud LLM fallback), Docker Compose, GitHub GraphQL API
(read-only).

## Intentionally deferred

Scope that was consciously considered and rejected or postponed — not forgotten, not a gap to
re-propose as new:

- **Multi-tenant auth / RBAC** (roadmap Phase 7.2) — this is a single-tenant internal tool today.
- **WebSocket-based live multi-user collaboration** (roadmap Phase 7.3) — SSE (one-way
  server→client) already covers the current single-viewer-at-a-time real-time needs; a full
  bidirectional WebSocket layer isn't justified yet.
- **GitHub MCP integration** (roadmap Phase 7.4) — the GitHub GraphQL client in
  `execution/github_sync.py` is hand-rolled and deliberately read-only; adopting a general-purpose
  MCP GitHub server would need to preserve that same read-only guarantee before it's worth the
  swap.
- **An external/public API contract** — see `api/README.md`. This is a self-contained dashboard
  with no external API consumers today, so `docs/api/` stays empty rather than documenting
  something that doesn't exist.
- **Auto-discovering new repos under a GitHub org** — `github_sync` only ever syncs Tasks inside
  Projects that already have `github_repo` manually configured; it never creates a Project from an
  org's repo listing. Projects stay a deliberately manual, human-curated set.
