# V.I.S.I.O.N. Documentation — Second Brain

`docs/` is the single source of truth for this project. If a fact about V.I.S.I.O.N. isn't
written down here, it isn't decided — no matter how many times it was said in chat.

## Map

- **[`00-overview.md`](00-overview.md)** — what this project is, the stack, and what's
  intentionally out of scope.
- **[`01-roadmap.md`](01-roadmap.md)** — the canonical phase/status table. Where the project is
  right now.
- **[`02-product-vision.md`](02-product-vision.md)** — the Lean Canvas: business problem, target
  users, outcomes, and the riskiest-assumption experiment plan.
- **`adr/`** — Architecture Decision Records. One immutable file per durable, hard-to-reverse
  technical decision. Never edited after acceptance; a rethink gets a new ADR that supersedes it.
- **`architecture/`** — binding technical guardrails, written as rules, not narrative. A change
  that violates one of these should be an easy, unambiguous review rejection.
- **`api/`** — the external contract other consumers rely on. Currently empty — see
  [`api/README.md`](api/README.md) for why.
- **`governance/`** — how work happens here: the data-operation-vs-system-change dispatch rule,
  the confirmation policy, and the agent execution protocol. Process rules, not tech decisions
  (those are `adr/`).
- **`domains/`** — agent-maintained live maps of the *current* codebase: architecture, business
  logic/schema, every route, request/job flow wiring, and test coverage. Never aspirational,
  never historical — update these in the same change that alters what they describe.
- **`memory/`** — durable, curated knowledge: established patterns, coding standards, what an
  agent may do unsupervised, and — critically — **[`memory/documentation_policy.md`](memory/documentation_policy.md)**,
  the map of which doc to update for which kind of change. That file is what keeps the rest of
  this tree from silently going stale.
- **`skills/`** — repeatable procedures for recurring tasks (a playbook, not a knowledge map).
- **`reports/`** — dated, append-only historical record. `reports/issues/` is what actually
  shipped and was verified, one file per closed roadmap item. `reports/specs/` is the flip side —
  the work-order spec written *before* each of those items was built. Neither is ever rewritten
  in place; a correction gets a new dated entry.

## What does NOT belong here

- Runtime config, secrets, `.env` values.
- Application source code (this describes the code, it isn't the code).
- Raw, per-session working notes — those go in `.agent/` (see `.agent/README.md`), and are never
  cited as evidence of what's true about the project.

## Governing principles

1. `docs/` is the only source of truth — see above.
2. Exactly one root entrypoint per agent (`CLAUDE.md`, `GEMINI.md`, `AGENTS.md` — kept identical
   in substance, only the named agent differs) reads first. They never
   duplicate content — they only point in here.
3. Currency over completeness — `domains/` and the roadmap are updated in the *same* change that
   alters what they describe, not as a follow-up.
4. `domains/`/roadmap describe the present; `adr/`/`reports/` describe the past. Don't conflate
   them.
5. `.agent/` is disposable session config, not project knowledge.
6. One fact, one owner — never let the same status be duplicated across two files.
