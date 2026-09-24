# System Architecture

## Module map

```
dashboard_app/
├── app/
│   ├── main/routes.py       # all Flask routes — see domains/api_endpoints.md
│   ├── models.py            # SQLAlchemy models — see domains/business_logic.md
│   ├── commands.py          # `flask seed` / `flask process-repetitions` CLI commands
│   ├── extensions.py        # db, migrate, SQLite WAL pragma setup
│   ├── utils/sse.py         # MessageAnnouncer — the SSE fan-out used by trigger_ui_refresh
│   ├── utils/trigger.py     # trigger_task_update / trigger_project_update helpers
│   ├── utils/htmx_utils.py  # is_htmx / picovoice_access_key / is_locked context processor
│   ├── utils/timezone_utils.py  # DISPLAY_TIMEZONE conversion — see adr/0002; Flask-free so
│   │                            # execution/ can import it without an app context
│   ├── utils/jinja_filters.py   # registers the |localtime template filter
│   ├── static/               # CSS, JS (Alpine.js glue, wake-word.js, voice.js)
│   └── templates/            # HTMX partials + the persistent HUD base.html
├── instance/app.db          # the live SQLite DB (WAL mode; tracked in git in this project)
└── migrations/versions/     # Alembic migrations

execution/
├── agent_actions.py         # the CLI + function surface every agent (human, Claude Code, the
│                             # LLM Orchestrator) calls for data operations — see governance/
├── db_client.py             # shared DB session factory (WAL-enabled)
├── github_sync.py           # read-only GitHub GraphQL polling — see architecture/ + business_logic.md
├── github_sync_worker.py    # long-running two-cadence loop entrypoint for the github-sync container
├── repetition_processor.py  # daily/weekly/monthly Task status resets (local-day boundary)
└── backfill_github_created_at.py  # one-off: populate Task.github_created_at from GitHub

orchestrator/
├── brain.py                 # the Orchestrator control loop
├── gateway.py                # LLM backend routing (Ollama local / NVIDIA NIM cloud)
├── manifest.py               # TOOL_MANIFEST — the technical contract for every tool the LLM can call
├── prompts.py                 # SYSTEM_PROMPT — the LLM's operating instructions (embeds the manifest)
├── validator.py              # generic, manifest-driven validation of LLM tool calls
└── test_gateway.py           # manual diagnostic script (not a unittest suite, not under tests/) —
                                # makes a real NVIDIA NIM call to verify cloud connectivity/fallback;
                                # lives inside orchestrator/ so it IS copied into the built Docker
                                # image (unlike tests/, see domains/test_coverage.md), even though
                                # it isn't part of the automated test suite
```

## AI Orchestrator

The Orchestrator is a local-first LLM router that interprets natural-language intent and maps it
to the same `execution/agent_actions.py` functions available to any other agent working in this
repo.

### Brain (`orchestrator/brain.py`)

The main control loop.
- **Max iterations**: 30 (prevents runaway execution) — verified directly in code; do not trust an
  older doc's number without re-checking, this value has drifted before.
- **Loop chaining**: can perform a sequence of actions (e.g. `search_entities` → `create_task`) in
  a single turn.
- **Loop prevention**: detects a repeated `action:params` signature (any action, not only
  mutations — e.g. a duplicate `search_entities` call trips it too) and stops before repeating it.
- **Action execution**: dynamically maps LLM-requested tool names to functions in
  `execution/agent_actions.py`.
- **LLM-output repair**: before parsing, the Brain auto-corrects two classes of malformed LLM
  output rather than failing outright — a `params` value that's a hallucinated string (single-quote
  JSON, or a `key=value` query string parsed via `urllib.parse.parse_qs`) gets coerced into a real
  dict, and a mistyped `action` key (`.action`, `.actio`, `actio`, `action_name`, `tool`) gets
  renamed to `action`.
- **Terminal actions**: only `chat_response` and `navigate_to` stop the loop and return a final
  response — every other action (all CRUD/list/search calls) always continues to the next
  iteration by design, per the code's own comment: "Listing/Search tools are non-terminal so the
  LLM can read their results and continue working" (`brain.py`) — this is a fixed rule, not a
  per-call judgment call by the model.
- **`warmup()`**: a separate method that POSTs `{"model": ..., "keep_alive": -1}` to Ollama to
  pre-load the model into memory ahead of the first real request.

### LLM Gateway (`orchestrator/gateway.py`)

A routing layer for LLM requests.
- **Backends**: Local (Ollama, default `phi3.5` — corrected 2026-08-27; an earlier pass through
  this doc said `llama3.1`, which is not what the code defaults to in either `gateway.py` or
  `brain.py`) and Cloud (NVIDIA NIM, OpenAI-compatible API, default model
  `nvidia/nemotron-4-340b-instruct`).
- **Fallback logic**: if the cloud backend fails, automatically falls back to the local Ollama
  instance.
- **Configuration**: `OLLAMA_HOST`, `OLLAMA_MODEL`, `NVIDIA_API_KEY`, `NVIDIA_MODEL`.

### Tool Manifest (`orchestrator/manifest.py`)

Defines the technical contract for every tool available to the LLM — descriptions, parameter
types, required fields. Covers CRUD for Systems, Projects, Tasks, and Employees; search;
navigation; and a conversational fallback (`chat_response`). This is the same contract
`docs/governance/01-development-workflow.md`'s data-vs-system-change rule maps a data operation
onto.

## Operational flow

1. **User input** — received via the Dashboard chat UI (or voice, transcribed client-side).
2. **Context assembly** — the last 10 messages are pulled from the `ChatMessage` table as history.
3. **LLM inference** — the Gateway sends the prompt + history to the selected backend.
4. **Action parsing** — the Brain extracts JSON from the LLM response.
5. **Validation** — `orchestrator/validator.py` checks the JSON against the Tool Manifest (purely
   generic/manifest-driven — it has no entity-specific rules hardcoded).
6. **Execution** — the chosen action runs via `agent_actions.py`.
7. **Feedback loop** — the tool's result is appended to history; the loop continues to the next
   iteration unless the action was one of the two fixed terminal actions (`chat_response`,
   `navigate_to` — see "Terminal actions" above), not a per-call judgment call by the model.
8. **UI notification** — navigation intents trigger an `HX-Trigger` header
   (`vision-navigation`); data mutations trigger an SSE update via `trigger_ui_refresh()` — see
   `domains/flows.md`.
