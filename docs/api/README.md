# API Contracts — Intentionally Empty

This folder is reserved for the template's `api/` slot — the external contract other consumers
rely on. It's empty on purpose, not by omission: V.I.S.I.O.N. is a self-contained, server-rendered
dashboard with no external API consumers today. Every Flask route either renders a full page,
returns an HTMX partial for the same UI, or is an internal SSE-trigger endpoint — see
[`../domains/api_endpoints.md`](../domains/api_endpoints.md) for the full route index.

If this project ever grows a real external API surface (a JSON API meant for another service or a
third-party integration to consume), that's when a file goes here — one per surface, matching the
running code exactly, ideally pinned by a test so it can't silently drift.
