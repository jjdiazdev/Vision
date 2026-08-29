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

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose
- [Ollama](https://ollama.com/) (only if you want to run it locally outside Docker — the `ollama` service in Compose already handles this for you otherwise)
- A GitHub Personal Access Token, **only if you want the GitHub-monitoring feature** (see below) — everything else works without one.

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-repo/v-i-s-i-o-n.git
    cd v-i-s-i-o-n
    ```

2.  **Environment Setup:**
    ```bash
    cp .env.example .env
    ```
    Open `.env` and set at minimum:
    - `SECRET_KEY` — any random string.
    - `OLLAMA_MODEL` — defaults to `phi3.5`; any model Ollama can pull works.
    - `GITHUB_TOKEN` and the two sync-interval vars — **only needed for GitHub monitoring**, see the dedicated section below. Leave `GITHUB_TOKEN` unset and the rest of the dashboard works fine; the `github-sync` container will simply have nothing to poll.
    - The `NVIDIA_*` / `OPENAI_*` / `ANTHROPIC_*` / `GEMINI_*` keys are optional — only needed if you turn on a cloud LLM backend from the HUD's settings.

3.  **Launch with Docker:**
    ```bash
    docker-compose up --build
    ```
    This builds and starts all three services — `web`, `github-sync`, and `ollama` — in one command. The `web` container applies any pending database migrations automatically on startup (its entrypoint runs `flask db upgrade` before the app starts) — you don't need to create or seed `dashboard_app/instance/app.db` yourself; it's created from scratch on first run and isn't tracked in git. On first run, Ollama also automatically pulls the model specified in `.env` (e.g. `phi3.5`), which can take several minutes depending on your connection.

4.  **Access the Dashboard:**
    Open `http://localhost:5001` in your browser.

5.  **Subsequent restarts:** after pulling code changes, `docker-compose up --build` again to rebuild the images; day-to-day, `docker restart v-i-s-i-o-n-web-1` (or `v-i-s-i-o-n-github-sync-1`) is enough to pick up a file that was `docker cp`'d in without a full rebuild — see [`docs/governance/01-development-workflow.md`](docs/governance/01-development-workflow.md) for exactly when each is needed.

---

## 🔗 Monitoring GitHub Development

V.I.S.I.O.N. can track Issues and Pull Requests across your GitHub organization's repos automatically, entirely read-only — it never creates, edits, closes, or comments on anything in GitHub. The full guardrail is documented in [`docs/architecture/01-github-readonly-guardrail.md`](docs/architecture/01-github-readonly-guardrail.md); the practical steps to turn it on are below.

### 1. Create a read-only GitHub token

Generate a Personal Access Token with **only** these permissions, all set to **Read-only**:
`Contents`, `Metadata`, `Issues`, `Pull requests`, `Commit statuses`.

- A **fine-grained PAT** works if your GitHub organization allows fine-grained PAT access for members and the token's Resource Owner is set to that organization.
- Otherwise, a **classic PAT** with the `repo` scope is the reliable fallback for private repos (a classic PAT can't be restricted to read-only at the GitHub UI level, but this project's code enforces the read-only limit in software regardless — see the guardrail doc).

### 2. Configure `.env`

```bash
GITHUB_TOKEN=your_github_personal_access_token_here
SYNC_INTERVAL_SECONDS=5       # fast recheck of Tasks already In-Progress/Testing
DISCOVERY_INTERVAL_SECONDS=60 # slow full scan: discovers new issues, reconciles everything
```
The defaults above are sensible for most cases — only tune them if you have unusually high GitHub API rate-limit pressure (many repos, many Tasks) or want faster/slower reflection latency.

### 3. Bootstrap your organization's data (recommended first step)

Before the automatic sync has anything to sync, **populate the database once** — otherwise you'd be creating one Project at a time by hand and waiting for Employees to trickle in as issues happen to get scanned. The fastest way: ask your AI agent (Claude Code, or any agent with GitHub MCP access) to do it for you in one pass, e.g.:

> "Use the GitHub MCP to read the `my-organization` organization's repositories and their contributors; create the System, one Project per repo, and one Employee per contributor."

The agent reads your org's repos and each one's contributors read-only via GitHub MCP, then creates the matching records with `execution/agent_actions.py` (`data:`-style operations — see below). **One thing matters for this to work correctly**: each Employee's `name` must be set to the contributor's exact GitHub login (e.g. `Jorman-ops`), not a "nicer" display name — `github_sync`'s own auto-assignment matching (see below) looks up an issue's assignee by that exact string, and a mismatch creates a *second*, duplicate Employee instead of reusing the one you just created.

### 4. Link a Project to a GitHub repo manually

For a single repo, or to add one more later without re-running the bootstrap above:

```bash
docker exec v-i-s-i-o-n-web-1 python -m execution.agent_actions project --create "my-repo" --github-repo "Organization/my-repo"
```

This does two things automatically: creates the Project, and — since no `--system-id` was given — derives and links its parent System from the repo owner (`Organization`), creating that System too if it doesn't exist yet. To link an *existing* Project to a repo instead of creating a new one, or to point it at a specific System explicitly:

```bash
docker exec v-i-s-i-o-n-web-1 python -m execution.agent_actions project --update <PROJECT_ID> --github-repo "Organization/another-repo" --system-id <SYSTEM_ID>
```

No restart is needed — the next scheduled sync cycle (within `DISCOVERY_INTERVAL_SECONDS`) picks up the newly linked repo on its own.

### 5. What you get, automatically

Once a Project is linked:
- Every open Issue becomes a Task, with its GitHub assignee mirrored to an Employee (auto-created on first sight, matched by exact GitHub login — see step 3 above) and its Issue/PR numbers shown as clickable links straight to GitHub.
- Task status is computed from live GitHub state, not set by hand: an issue with no PR yet is `Todo`; with an open linked PR, `Testing`; once that PR merges (or the issue closes with a completed PR), `Done`; if a PR tied to the issue was closed *without* merging, or the issue closed with no completed PR at all, the Task flips to `Blocked` — regardless of whatever status a human had set, since a closed issue is treated as the most authoritative signal there is.
- A Task manually set to `In-Progress` is left alone by GitHub sync except to advance it forward (to `Testing`/`Done`) — it's never silently reset back to `Todo`. But **only** a Task already `In-Progress` or `Testing` gets the fast 5-second recheck; a Task still sitting at `Todo` (never manually moved) is only picked up by the slower, full `DISCOVERY_INTERVAL_SECONDS` (60s default) scan — so if you want near-instant status updates on a specific Task, mark it `In-Progress` by hand first.
- Setting a **Project's own** status to `Blocked` pauses GitHub polling for that repo entirely and hides its Tasks from the Tasks view — they'd otherwise show a status that's no longer being kept current.
- The Tasks view sorts by status in a fixed order — `Testing` → `In-Progress` → `Todo` → the `Repeat *` statuses → `Done` → `Blocked` — so what's actively moving always surfaces above what's finished or stuck.
- The Systems (`/systems`) and Projects (`/projects`) views, and the Tasks view's System/Project filters, all reflect this automatically — no separate "sync" button to click anywhere.

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
2.  **Generate the password hash** — pick your own password in place of `yourpassword`:
    ```bash
    python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('yourpassword'))"
    ```
3.  **Paste both into `.env`**, then **double every `$` in the hash to `$$`**:
    ```bash
    SECRET_KEY=<output from step 1>
    ADMIN_PASSWORD=<output from step 2, with every $ doubled to $$>
    ```
    This last part matters: docker-compose treats a bare `$word` in `.env` as a variable reference and
    silently blanks it out if that variable isn't set — a Werkzeug hash always contains `$` as a field
    separator (e.g. `scrypt:32768:8:1$salt$hash`), so pasting it in unescaped corrupts the stored hash
    and every login attempt fails with no visible error.
4.  **Restart (or recreate) the `web` container** for the new `.env` values to load —
    `docker restart` alone does *not* re-read `.env` for an already-running container; use
    `docker-compose up -d` to pick up the change.

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
