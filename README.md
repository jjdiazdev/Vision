# V.I.S.I.O.N. 
### Virtual Interactive System for Information and Orchestration Networks

V.I.S.I.O.N. is a **Natural Language Operating System (NLOS)** and **Cognitive Project Orchestrator**. It transforms the traditional static dashboard into an "agentic" UI, allowing users to manage complex development lifecycles, company data, and project workflows through natural conversation and voice commands — including real, live monitoring of GitHub Issues and Pull Requests across your organization's repositories.

---

## 🚀 The Vision
In modern software engineering, the gap between *intent* and *execution* is often filled with manual clicks, form filling, and context switching. V.I.S.I.O.N. bridges this gap by using a local AI agent to interpret natural language commands and execute them directly against your project's infrastructure — while a background worker keeps that infrastructure in sync with what's actually happening on GitHub.

- **Natural Language Operating System (NLOS):** No more nested menus. Just tell the system what you want to do.
- **Agentic UI:** A UI that doesn't just display data, but understands and acts upon it.
- **Local-First AI:** Powered by Ollama, ensuring your data and reasoning stay on your hardware, with an optional cloud fallback for harder reasoning.
- **Live GitHub Awareness:** Issues and Pull Requests across your GitHub organization's repos are reflected automatically, read-only, with zero manual data entry.

---

## 🏗️ Architecture

V.I.S.I.O.N. is built on a modern, high-performance stack designed for real-time interaction and agentic execution.

*   **Frontend:** 
    *   **Alpine.js:** Lightweight state management for the "Iron Man HUD" interface.
    *   **HTMX:** Powering the "Single Page Application" (SPA) feel with surgical, partial HTML updates.
    *   **Web Speech API:** Real-time voice-to-action transcription.
*   **Backend:** 
    *   **Flask (Python):** The central nervous system handling orchestration, routing, and data management.
    *   **SQLAlchemy (SQLite WAL Mode):** Robust data persistence with Write-Ahead Logging to allow concurrent access by the web app and background agent scripts.
*   **AI Orchestrator:**
    *   **Ollama:** Running local models (default `phi3.5`, configurable) for reasoning.
    *   **NVIDIA NIM (optional cloud fallback):** A "High Performance" toggle in the HUD routes requests to a cloud model instead, with automatic fallback back to local Ollama if the cloud call fails.
    *   **Tool Manifest:** A dynamic mapping system that translates NL intents into Python function calls within `agent_actions.py`.
*   **GitHub Sync:**
    *   A dedicated `github-sync` container polls GitHub's GraphQL API on two cadences (fast recheck of active work, slow full discovery) and reflects issue/PR state into the local database — **strictly read-only**, it never writes anything back to GitHub. See the "Monitoring GitHub Development" section below.
*   **Deployment:**
    *   **Docker Compose:** Multi-container orchestration — `web` (the dashboard), `github-sync` (the background worker above), and `ollama` (local inference).

---

## 🧬 Data Model

Three levels, top to bottom:

- **System** — a GitHub organization (e.g. `your-organization`). Owns one or more Projects.
- **Project** — a GitHub repository. Belongs to a System (auto-linked from the repo owner, see below).
- **Task** — a unit of work belonging to a Project, optionally mirroring a GitHub Issue and/or Pull Request.

Full schema and business rules: [`docs/domains/business_logic.md`](docs/domains/business_logic.md).

---

## 🛠️ Key Features

- **Persistent HUD Chat:** A sleek, non-intrusive chat interface that follows you across the entire dashboard.
- **Voice-to-Action:** Command your workspace hands-free. "Create a new project named Apollo" or "Assign the bug fix to John."
- **Real-Time UI Synchronization:** When the agent — or the GitHub sync worker — makes a change, the UI updates instantly via Server-Sent Events, no page refresh needed.
- **Visual Feedback Loop:** The HUD "pulses" while the AI is thinking, providing a visceral connection between the user and the system.
- **Atomic Agent Actions:** A modular execution layer (`agent_actions.py`) that handles everything from project creation to task assignment.
- **Automatic GitHub Task Sync:** Once a Project is linked to a GitHub repo, its Issues/PRs appear as Tasks automatically, with status (`Todo`/`Testing`/`Done`/`Blocked`) computed from real issue/PR state — no manual data entry, and never a write back to GitHub.
- **Notification History:** The Dashboard keeps a persisted history of every toast — not just the ephemeral 5-second popup. Each entry shows the message, the linked team member (when there is one), and the timestamp; click a Task-related entry to jump straight to the Tasks view pre-filtered to that task's project and assignee at once. Dismiss an entry once you've dealt with it — it slides out and the rest reflow to fill the gap.
- **Toast Sound Notifications:** Every toast now plays a short sound, so an automatic status change (e.g. from the GitHub sync worker) doesn't go unnoticed just because you weren't looking at the screen — see [Sound Notifications](#-sound-notifications) below to set it up.
- **Weekly Implementation Plans:** Import the plan the team is executing this cycle (its issues across your org's repos plus their dependency graph). Progress then counts only that plan's issues, the Tasks list shows only them, and **Tasks → Graph** draws the plan as a live, horizontal dependency graph whose nodes change color and symbol as PRs open, fail CI, get changes requested, merge and close — see [Weekly Implementation Plans](#-weekly-implementation-plans) below.
- **Admin Password Gate:** A single shared password blocks the whole dashboard until entered, resetting whenever the browser is fully closed and reopened — see [Admin Password Gate](#-admin-password-gate) below to configure one.

---

## 📂 Project Structure

```text
.
├── dashboard_app/          # Flask Web Application
│   ├── app/                # Core App Logic (Models, Routes, Templates)
│   │   ├── main/           # Main Blueprint
│   │   ├── static/         # CSS/JS (Alpine, HTMX logic)
│   │   └── templates/      # HTMX Partials & HUD Base
│   └── instance/           # SQLite Databases
├── execution/              # The Agent's Hands
│   ├── agent_actions.py    # Executable Python scripts for NL mapping
│   ├── github_sync.py      # Read-only GitHub GraphQL polling
│   └── db_client.py        # Shared DB connection (WAL-enabled)
├── orchestrator/           # The AI Orchestrator (Brain, LLM Gateway, Tool Manifest)
├── docs/                   # Project documentation — the source of truth, see docs/README.md
└── .agent/                 # Disposable, session-scoped agent notes only — not project knowledge
```

---

## 🗺️ Roadmap

See [`docs/01-roadmap.md`](docs/01-roadmap.md) for the canonical, current phase/status table —
not duplicated here to avoid the two drifting apart.

---

## ⚙️ Setup & Installation

This is the full path from a clean clone to a dashboard tracking your own GitHub organization.
Run every command from the repository root. Commands use Docker Compose v2 (`docker compose`,
with a space) and address containers by **service name** (`docker compose exec web …`), so they
work whatever the folder is called.

### Prerequisites
- [Docker](https://www.docker.com/) with the Compose v2 plugin (`docker compose version`).
- A GitHub account with access to the organization and repositories you want to monitor.
- Port `5001` free (the dashboard) and, unless you follow step 2, port `11434` (Ollama).

### Step 1 — Create a read-only GitHub token

V.I.S.I.O.N. only ever **reads** GitHub; the token should not be able to do anything else
(see [`docs/architecture/01-github-readonly-guardrail.md`](docs/architecture/01-github-readonly-guardrail.md)).

1.  GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens →
    Generate new token**.
2.  **Resource owner**: your organization. **Repository access**: *Only select repositories*, and
    pick the repos you want to monitor (you can add more later by editing the token).
3.  **Repository permissions**, all **Read-only**:
    - Contents, Metadata, Issues, Pull requests — issue and PR state.
    - Commit statuses — CI color in the plan graph.
    - Checks — also recommended: GitHub Actions reports through check runs.
4.  If your organization requires approval for fine-grained tokens, an owner approves it under
    **Organization settings → Personal access tokens → Pending requests**. Until then every repo
    reads as "not found".

If your organization does not allow fine-grained tokens, a classic token with the `repo` scope
works too. It cannot be restricted to read-only on GitHub's side, but this project's code refuses
to send any write (`execution/github_sync.py::graphql_query`).

### Step 2 — Check the Ollama port

The `ollama` service publishes port `11434`. If Ollama already runs on your machine
(`ss -ltn | grep 11434`), either stop it (`sudo systemctl stop ollama`), or keep it and create a
local `docker-compose.override.yml` (git-ignored) so the container does not publish the port (the
dashboard reaches it over Docker's internal network and does not need it on the host):

```yaml
services:
  ollama:
    ports: !reset []
```

### Step 3 — Clone and build

```bash
git clone <this repository's URL> vision
cd vision
docker compose build
```

### Step 4 — Configure `.env`

```bash
cp .env.example .env
```

Then edit `.env` (it is git-ignored; never commit it):

| Variable | Value |
|---|---|
| `SECRET_KEY` | A random secret: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | The dashboard password **hash** — see below |
| `GITHUB_TOKEN` | The token from step 1 |
| `DISPLAY_TIMEZONE` | Your IANA zone, e.g. `America/Caracas` (default `UTC`) |
| `SYNC_INTERVAL_SECONDS` / `DISCOVERY_INTERVAL_SECONDS` / `PLAN_SYNC_INTERVAL_SECONDS` | Leave at `5` / `60` / `15` unless you hit GitHub rate limits |
| `OLLAMA_MODEL` | Defaults to `phi3.5`; any model Ollama can pull |
| `NVIDIA_*` / `OPENAI_*` / `ANTHROPIC_*` / `GEMINI_*` | Optional — only for a cloud LLM backend in the HUD settings |

**Password hash.** Generate it with the image you just built, so your host needs no Python
packages; it prompts for the password without echoing it:

```bash
docker compose run --rm --no-deps --entrypoint python web -c "import getpass; from werkzeug.security import generate_password_hash as g; print(g(getpass.getpass()))"
```

Paste the output into `ADMIN_PASSWORD=` and **double every `$` to `$$`**
(`scrypt:32768:8:1$$salt$$hash`). Compose treats a bare `$word` as a variable and silently blanks
it, which makes every login fail with no visible error. Details:
[Admin Password Gate](#-admin-password-gate).

### Step 5 — Start everything

```bash
docker compose up -d
docker compose logs web | grep -i -e "running upgrade" -e error
```

This starts `web` (the dashboard), `github-sync` (the read-only GitHub worker) and `ollama`. On
every start `web` applies pending database migrations; on a first run that creates
`dashboard_app/instance/app.db` from scratch (it is git-ignored). The first start also pulls the
Ollama model, which can take several minutes.

Open **http://localhost:5001** and log in with your password.

### Step 6 — Choose the repositories to monitor

Only repositories linked to a **Project** are monitored; the worker never discovers repos on its
own. Link one Project per repo:

```bash
docker compose exec web python -m execution.agent_actions project --create api --github-repo your-org/api
docker compose exec web python -m execution.agent_actions project --create web --github-repo your-org/web
docker compose exec web python -m execution.agent_actions project --list
```

The parent **System** (your organization) is created automatically from the repo owner. No restart
is needed: the next discovery cycle (within `DISCOVERY_INTERVAL_SECONDS`) picks the repos up.

> **First sync reads the whole history.** Each repo's first pass reads every issue, open and
> closed, and creates one Task per issue. Large repos take several 60-second cycles and use more of
> your GitHub API budget. To stop reading a repo, set its Project to **Blocked** in `/projects`.

To link an existing Project to another repo, or assign it to a specific System:

```bash
docker compose exec web python -m execution.agent_actions project --update <PROJECT_ID> --github-repo your-org/another-repo --system-id <SYSTEM_ID>
```

### Step 7 — Verify the sync

```bash
docker compose logs -f github-sync
```

| You see | Meaning |
|---|---|
| `Created Task for your-org/api#N …` | Working |
| `Repository … not found or not accessible` | The token can't see that repo — check step 1 (repo selected, org approval) |
| `GITHUB_TOKEN is not set` | `.env` wasn't loaded — `docker compose up -d --force-recreate` |
| `GitHub rate limit low … pausing` | Budget below 50 points; every cadence resumes on its own at the next discovery check |

### Step 8 — Import your current plan (optional, recommended)

To make progress count only this cycle's issues and get the live dependency graph, import your
plan — see [Weekly Implementation Plans](#-weekly-implementation-plans).

### Day-to-day

- **After pulling code changes:** `docker compose up -d --build` rebuilds and restarts.
- **After editing `.env`:** `docker compose up -d --force-recreate` (`docker restart` keeps the
  old environment).
- **Back up the database** before upgrades: `cp dashboard_app/instance/app.db app.db.bak` (with
  the containers stopped, or include the `-wal` file).
- The exact edit-vs-restart rules for working on the code are in
  [`docs/governance/01-development-workflow.md`](docs/governance/01-development-workflow.md).

---

## 🔗 Monitoring GitHub Development

V.I.S.I.O.N. tracks Issues and Pull Requests across your organization's repos automatically, and
entirely read-only — it never creates, edits, closes or comments on anything in GitHub. Setup is
steps 1, 6 and 7 above.

### Assignees and team members

An issue's assignee becomes a team member (Employee) automatically, matched by **exact GitHub
login**. If you create team members by hand (or ask an agent to bootstrap them from the org's
contributors), set each `name` to the contributor's exact login (e.g. `octocat`), not a display
name; otherwise the sync creates a second, duplicate member.

### What you get, automatically

Once a Project is linked:
- Every issue becomes a Task, with its GitHub assignee mirrored to a team member and its Issue/PR
  numbers shown as links straight to GitHub.
- Task status is computed from live GitHub state, not set by hand: an issue with no PR yet is
  `Todo`; with an open linked PR, `Testing`; once that PR merges (or the issue closes with a
  completed PR), `Done`; if a PR tied to the issue was closed *without* merging, or the issue
  closed with no completed PR at all, `Blocked` — whatever a human had set, since a closed issue
  is the most authoritative signal there is.
- A Task manually set to `In-Progress` is only ever advanced by the sync (to `Testing`/`Done`),
  never reset to `Todo`. Only Tasks already `In-Progress` or `Testing` get the fast 5-second
  recheck; a `Todo` Task is refreshed by the 60-second discovery scan — mark a Task `In-Progress`
  by hand for near-instant updates.
- Setting a **Project's own** status to `Blocked` pauses GitHub polling for that repo and hides its
  Tasks from the Tasks view.
- The Tasks view sorts by status — `Testing` → `In-Progress` → `Todo` → `Repeat *` → `Done` →
  `Blocked` — so active work surfaces first.
- The Systems (`/systems`) and Projects (`/projects`) views and the Tasks filters reflect all of
  this automatically.

---

## 📐 Weekly Implementation Plans

GitHub monitoring alone counts every open issue of a repo. When the team works in short cycles
(plan, implement, test, next plan), only the issues in **this** plan should move the percentage.

1.  **Write the plan as usual** — a Markdown document listing the issues per repo and ending in a
    Mermaid `graph LR` of their dependencies (`-->` from the base branch, `==>` stacked PRs,
    `-.->|label|` conditions such as "contract" or "staging"). Keep it out of this repo.
2.  **Ask your AI agent to import it**, e.g. *"data: import the plan in ~/plans/week-43.md"*. The
    agent converts it to the plan JSON following
    [`docs/skills/import-plan/SKILL.md`](docs/skills/import-plan/SKILL.md) (keep that JSON out of
    the repo too) and loads it:
    ```bash
    docker compose cp /path/to/plan.json web:/tmp/plan.json
    docker compose exec web python -m execution.agent_actions plan --import /tmp/plan.json
    ```
    The import is validated (no cycles, every repo in one org and already linked as a Project —
    step 6 above) and becomes the System's active plan. Manage plans afterwards with
    `plan --list`, `--activate ID`, `--deactivate ID` and `--delete ID`.
3.  **What changes**:
    - A Project in the active plan shows `(merged + closed) / plan issues`, with an "N/M in plan"
      mark. Other Projects keep the all-Tasks percentage.
    - The Tasks list shows only the plan's issues; switch **Plan only → All tasks** to see the rest.
    - **Tasks → Graph** (top right) draws the plan per repo, left to right. Node color and symbol
      follow the plan's status rule: ○ no PR, ◐ PR open, ⚠ CI failing or changes requested,
      ✓ merged with the issue still open, ✔ closed. A stacked edge (`══`) relaxes to a plain one
      once its parent merges. Click a node for its PR, CI, review and dependencies. Drag a
      repo's graph by its header (or focus it and use the arrow keys) to arrange the canvas; the
      layout is remembered in your browser, and **Reset layout** restores it. The button in the canvas's
      bottom-right corner (or the `F` key) shows just the legend, controls and canvas full
      screen; `Esc` leaves it.
4.  **Live updates**: the `github-sync` worker re-reads the plan's issues every
    `PLAN_SYNC_INTERVAL_SECONDS` (15 by default) and the graph updates on its own: a changed node
    simply takes its new color and symbol, with no animation. A red CI needs the token's
    **Commit statuses** (and, for GitHub Actions, **Checks**) read permission — step 1.

---

## 🔒 Admin Password Gate

A single shared password protects the whole dashboard — everyone who knows it gets full access; there
are no separate per-person accounts. `ADMIN_PASSWORD` in `.env` holds a **hash** of that password, not
the plaintext. Set this up once per environment (a fresh `.env` on a new machine, or after rotating
the password):

1.  **Generate a `SECRET_KEY`** (it also signs the login session cookie, so it must be a real secret,
    not left at the placeholder default):
    ```bash
    python3 -c "import secrets; print(secrets.token_hex(32))"
    ```
2.  **Generate the password hash** with the built image (prompts without echoing; nothing needs to
    be installed on the host):
    ```bash
    docker compose run --rm --no-deps --entrypoint python web -c "import getpass; from werkzeug.security import generate_password_hash as g; print(g(getpass.getpass()))"
    ```
3.  **Paste both into `.env`**, then **double every `$` in the hash to `$$`**:
    ```bash
    SECRET_KEY=<output from step 1>
    ADMIN_PASSWORD=<output from step 2, with every $ doubled to $$>
    ```
    This last part matters: Compose treats a bare `$word` in `.env` as a variable reference and
    silently blanks it out if that variable isn't set — a Werkzeug hash always contains `$` as a field
    separator (e.g. `scrypt:32768:8:1$salt$hash`), so pasting it in unescaped corrupts the stored hash
    and every login attempt fails with no visible error.
4.  **Recreate the `web` container** for the new `.env` values to load —
    `docker restart` alone does *not* re-read `.env`; use `docker compose up -d --force-recreate web`.

Full design notes and known limitations (no per-user accounts, no brute-force lockout — deliberate,
not oversights): [`docs/architecture/02-admin-password-gate.md`](docs/architecture/02-admin-password-gate.md).

---

## 🔊 Sound Notifications

Every toast — whether from a manual edit, the AI agent, or the GitHub sync worker running in the
background — also plays a short sound, so an automatic change doesn't go unnoticed just because you
weren't looking at the screen. The sound file itself isn't bundled with this repo (no audio asset is
committed to `dashboard_app/app/static/sounds/`) — supply your own:

1.  Drop an MP3 at exactly this path: `dashboard_app/app/static/sounds/toast-notification.mp3`.
2.  No config, restart, or code change needed beyond having the file in place — `window.playToastSound()`
    (`base.html`) references that exact filename already. If the file is missing, toasts still display
    normally; the sound is silently skipped.

---

## 🗣️ Data Operations vs. System Changes (`data:` / `system:`)

Every request made to an AI agent working in this codebase (via the HUD chat/voice, or an AI coding agent like Claude Code) is treated as one of two kinds:

- **A data operation** — creating, updating, deleting, listing, or searching a System/Project/Task/Employee, or navigating between views. These execute immediately, with no code changes and no confirmation prompt (even for deletes).
- **A system change** — a bug fix, a new feature, a UI/style change, or anything that requires editing code. These go through the normal engineering workflow (read, edit, test).

The two are usually inferred automatically from how a request is phrased (a request about one specific, named entity with a management verb like "create"/"mark"/"delete" is a data operation; a request about the system, the code, or the design in general is a system change). When it's ambiguous — or you just want to be explicit — prefix your message:

- `data: <request>` — forces the data-operation interpretation.
- `system: <request>` — forces the system-change interpretation.

Example: `data: create a project named Apollo` always executes directly against the database; `system: add a button to export tasks to CSV` always goes through the code-change workflow, even though both mention a concrete-sounding noun. Full rule and reasoning: [`docs/governance/01-development-workflow.md`](docs/governance/01-development-workflow.md).

---

## 🤝 Contributing
V.I.S.I.O.N. is an evolving project. `docs/` is the source of truth for how work happens here —
start with [`docs/README.md`](docs/README.md), and see
[`docs/governance/01-development-workflow.md`](docs/governance/01-development-workflow.md) before
submitting pull requests.

---

**V.I.S.I.O.N.** — *See the code. Speak the action. Orchestrate the future.*
