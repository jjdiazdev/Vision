# Development Workflow

## Two kinds of request, and how to tell them apart

Every request in this project is one of two kinds:

- **Data operation** → execute directly via `execution/agent_actions.py`, no code touched: create,
  update, delete, list, or search Systems/Projects/Tasks/Employees, and navigation. Maps 1:1 to a
  function in that module and an entry in `orchestrator/manifest.py`'s `TOOL_MANIFEST`.
- **System change** → the normal engineering workflow (read, edit, test code): bugs, new
  features, UI/style changes, architecture, dependencies, Docker, templates, or any change to
  `orchestrator/`, `dashboard_app/app/`, `execution/`, etc.

**Disambiguation rule**: if the request matches an existing `agent_actions.py` function's
signature, it's a data operation; if it requires changing behavior or code, it's a system change.

**Practical signal**: a request about **one specific entity** (a concrete ID or name) with a
management verb ("create," "mark," "assign," "delete," "list," "search," "take me to") → data. A
request about **the system, the code, the design, or a structural class of things** ("fix,"
"add a function/endpoint/field," "change the color/design," "why does X fail," "optimize") →
system change, even if it names a specific entity (e.g. "add a new field to the tasks table" is a
schema migration, not a data operation).

If a request is genuinely ambiguous, ask before acting rather than assume — this is a separate
rule from `02-confirmation-policy.md`, which only covers `delete_*` on data already identified as
a data operation. No keyword is required for normal use; an explicit `dato:`/`sistema:` prefix at
the start of a message is an optional escape hatch that forces that interpretation without going
through inference.

### Examples

Data operations: "crea un proyecto llamado Apollo" · "marca la tarea 5 como Done" · "asigna la
tarea 12 a Juan" · "borra el empleado 3" · "lista los proyectos" / "busca el sistema Acme".

System changes: "arregla el bug de X" · "agrega un botón/endpoint/función para Z" · "cambia el
color del estado Done" · "agrega un campo nuevo a la tabla de tareas" (migración/esquema) · "haz
que el chat soporte Z".

## Running `agent_actions.py`

- The local Python environment does **not** have the project's dependencies installed (Flask,
  SQLAlchemy, etc.) — never run `agent_actions.py` directly on the host.
- Primary path — inside the `web` service's Docker container (defined in `docker-compose.yml`),
  which already has everything installed and mounted:
  ```bash
  docker exec vision-web-1 python -m execution.agent_actions <command> ...
  ```
- Available subcommands: `system`, `project`, `task`, `employee`, `search`, `navigate`.
- For anything not covered by the `argparse` CLI (e.g. calling `chat_response` or another loose
  module function), use an inline `python -c` inside the container importing the function
  directly.
- If the container isn't showing as running, check with `docker ps` first — don't assume it
  exists.
- **Important**: `docker-compose.yml` only mounts `dashboard_app/instance` as a volume — the rest
  of the code (`execution/`, `orchestrator/`, `dashboard_app/app/`, etc.) is copied into the image
  at build time, not live-mounted. A local edit to a `.py` file does **not** automatically reach
  the running container:
  - For an immediate effect without rebuilding: `docker cp <local file> vision-web-1:/app/<same path>`
    (fast, but lost if the container gets recreated).
  - For the change to persist in the image: rebuild with `docker-compose up --build` (confirm with
    the user before restarting the service, since it affects the running container).

## System changes: source code vs. container

- Every system change is edited **always in the repo's source code**, in this same working tree
  (`dashboard_app/`, `orchestrator/`, `execution/`, templates, etc.) — never directly inside the
  container. The container is a runtime environment, not the source of truth for code.
- Gunicorn/Flask load templates, routes, and models into memory when the process starts — a source
  edit alone doesn't reach the running container by itself (same volume-mounting reason as above).
  For the change to be visible in the browser, the container usually needs to be **restarted**
  (`docker restart vision-web-1`) after syncing the file with `docker cp`.
- **Claude Code does not restart the container on its own to verify a system change.** The correct
  flow is: (1) edit the source in the repo, (2) sync it to the container with `docker cp` if it
  should be ready to test, and (3) tell the user the restart command
  (`docker restart vision-web-1`) for them to run manually and verify the result themselves.
- Exception: `execution/agent_actions.py` subcommands invoked via
  `docker exec ... python -m execution.agent_actions ...` run as a fresh process every time, so a
  recent `docker cp` does take effect immediately there without a restart — the restart is only
  needed for changes that affect the long-running Flask/Gunicorn process (routes, templates,
  models, static assets).
