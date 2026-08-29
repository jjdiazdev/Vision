This roadmap is designed to be the "Master Blueprint" for your development team. It covers the transition from a standard dashboard to an **AI-Orchestrated SPA**.

Each phase is structured to be independent enough for milestone assignment but integrated enough to ensure the "Orchestrator" pattern works seamlessly.

***

# 🗺️ Vision Dashboard: AI-Orchestrator Implementation Roadmap

**Project Goal:** Transform the current Flask/SPA dashboard into an AI-powered agentic system where users can manage company data via Natural Language (Text/Voice) using a local Ollama LLM.

---

## 🏗️ Architecture Overview
*   **Frontend:** Alpine.js (UI State) + HTMX (Partial Swapping).
*   **Orchestrator:** Flask-based Logic Layer.
*   **Reasoning Engine:** Ollama (Llama 3.1 / Phi-3.5).
*   **Execution:** Existing `agent_actions.py` scripts.
*   **Deployment:** Docker Compose (Multi-container).

---

## 🛠️ Phase 1: Infrastructure & Containerization
**Goal:** Create a stable, isolated environment for the Web App and the AI service.

- [x] **1.1 Docker Compose Setup:** 
    - Create a `docker-compose.yml` with two services: `web` (Flask) and `ollama` (AI).
    - Configure shared volumes for the SQLite database (`app.db`) to ensure data persistence across containers.
- [x] **1.2 Database WAL Mode Verification:** 
    - Ensure `db_client.py` is correctly applying `PRAGMA journal_mode=WAL` to allow concurrent writes from the Flask app and the Agent scripts.
- [x] **1.3 Environment Configuration:** 
    - Setup `.env` files to handle Ollama API endpoints and model names (e.g., `OLLAMA_MODEL=llama3.1`).
- [x] **1.4 Ollama Model Prep:** 
    - Create a startup script or `entrypoint` to automatically pull the desired model (`llama3.1` or `phi3.5`) when the container starts.

---

## 🧠 Phase 2: The Orchestrator Logic (The Brain)
**Goal:** Build the bridge between human language and Python function execution.

- [x] **2.1 Tool Manifest Creation:** 
    - Create a structured JSON or Dictionary defining all functions in `agent_actions.py` (name, description, arguments).
- [x] **2.2 Prompt Engineering:** 
    - Design a **System Prompt** that forces the LLM to act as a "JSON-only Router." 
    - *Input:* "Create a project named Apollo."
    - *Output:* `{"action": "create_project", "params": {"name": "Apollo"}}`
- [x] **2.3 The Orchestrator Class:** 
    - Develop a Python service that:
        1. Sends user input to Ollama.
        2. Parses the JSON response.
        3. Dynamically maps and calls the correct function in `agent_actions.py`.
- [x] **2.4 Action Validation Layer:** 
    - Implement a "Sanity Check" to ensure the LLM doesn't attempt to call non-existent functions or pass invalid parameters.

---

## 💬 Phase 3: Frontend Chat Integration
**Goal:** Implement the persistent Chat interface within the Iron Man HUD.

- [x] **3.1 HUD State Management (Alpine.js):** 
    - Update `base.html` to manage the `chatOpen` state. 
    - Implement the persistent chat window that stays visible across SPA route changes.
- [x] **3.2 HTMX Messaging Pipeline:** 
    - Create a `/agent/chat` endpoint in Flask.
    - Use `hx-post` to send messages and `hx-target` to append responses to the chat bubble list.
- [x] **3.3 HUD "Pulse" Loading State:** 
    - Use Alpine.js to trigger a visual pulse in the HUD core while waiting for the LLM/Orchestrator to finish processing.

---

## 🎙️ Phase 4: Voice-to-Action Implementation
**Goal:** Allow the user to command the dashboard using their voice.

- [x] **4.1 Web Speech API Integration:** 
    - Implement a client-side JavaScript service (integrated with Alpine.js) to handle `SpeechRecognition`.
- [x] **4.2 Visual Voice Feedback:** 
    - Create a "Recording" UI state in the HUD that activates when the user clicks the Voice button.
- [x] **4.3 Transcription Pipeline:** 
    - Send the transcribed text directly to the same `/agent/chat` endpoint created in Phase 3.
- [x] **4.4 Silence Detection:** 
    - Add logic to automatically stop recording and send the command after 2 seconds of user silence.

---

## 🔄 Phase 5: Real-Time UI Synchronization (SPA Polish)
**Goal:** Ensure the dashboard updates automatically when the Agent makes a change.

- [x] **5.1 HTMX Out-of-Band (OOB) Updates:** 
    - Modify the Orchestrator response to return not just the chat message, but also the updated HTML partials (e.g., the Projects Table) using `hx-swap-oob="true"`.
- [x] **5.2 Targeted Refresh Logic:** 
    - If the Agent updates a Task, ensure ONLY the specific Task row or Process card is updated in the UI, preserving the SPA performance.
- [x] **5.3 Notification System:** 
    - Implement a "HUD Alert" component in Alpine.js to show "Action Successful" or "Error" messages in the corner of the screen.

---

## 🧪 Phase 6: Testing & Optimization
**Goal:** Ensure reliability and speed.

- [x] **6.1 Intent Testing:** 
    - Create a suite of test sentences to ensure the LLM correctly identifies which script to run (e.g., "Add John to the team" -> `create_employee`).
- [x] **6.2 Error Handling:** 
    - Handle cases where Ollama is offline or the model returns malformed JSON.
- [x] **6.3 Model Optimization:** 
    - Evaluate performance between Llama 3.1 8B and Phi-3.5 Mini to find the best balance between reasoning and response speed.


## 🚀 Phase 7: Advanced Orchestration & Collaboration (Future Implementation)
**Goal:** Transition from a single-user tool to a multi-tenant team ecosystem with hands-free navigation.

- [x] **7.1 Voice-Driven Spatial Navigation:** 
    - Map specific voice intents to frontend route changes (e.g., "Take me to Projects").
    - Implement smooth transitions between HUD views triggered solely by agent execution.
- [ ] **7.2 Multi-Tenant Auth & RBAC:** 
    - Implement user session management and Role-Based Access Control.
    - Create "Assignee" views for members and "Supervisory" views for project managers.
- [ ] **7.3 Contextual Real-Time Collaboration:** 
    - Deploy a real-time messaging pipeline (WebSockets) for project-specific chat.
    - Enable @mentions and notification pulses within the HUD for team updates.
- [ ] **7.4 GitHub MCP Integration & Task Sync:**
    - **Corrected 2026-08-27** — this item's checkbox reads as if no GitHub↔Task bridging exists
      yet; that's stale. A read-only GraphQL sync (`execution/github_sync.py` +
      `execution/github_sync_worker.py`, its own `github-sync` Docker service, two polling
      cadences, auto-status computation, employee auto-matching) already exists and is documented
      in `docs/domains/business_logic.md` and `docs/architecture/01-github-readonly-guardrail.md`.
      "Task Deep-Linking" specifically is also already done — `Task.github_url` links a task name
      straight to its GitHub issue/PR (see `docs/domains/business_logic.md`'s computed-properties
      section). What's still genuinely undone, and what this checkbox should be read as tracking:
    - Deploy an actual GitHub MCP (Model Context Protocol) server — the current implementation is
      a hand-rolled, deliberately read-only GraphQL client instead, by design (see
      `docs/00-overview.md`'s "Intentionally deferred" section).
    - Map local Employees to GitHub accounts via email verification — the current mechanism instead
      auto-matches on GitHub login name directly (`_resolve_employee_id`,
      `execution/github_sync.py`), with no email step.
- [x] **7.5 Hybrid Intelligence Strategy (Cloud API Fallback):**
    - Implement a "High Performance" toggle in the HUD settings to switch the Orchestrator's backend from local Ollama to a Cloud API (DeepSeek, Anthropic, or OpenAI).
    - Design a fail-safe mechanism that automatically falls back to the local model when internet connectivity is lost, ensuring system resilience.
    - Optimize cost-efficiency by using local models for simple routine tasks and Cloud APIs only for complex reasoning or high-latency scenarios.

***

### 📝 Next Steps for the Team:
1.  **Backend Team:** Start with **Phase 1** (Docker) and **Phase 2.1** (Function Mapping).
2.  **Frontend Team:** Focus on **Phase 3.1** (Chat UI) and **Phase 4.1** (Speech API).
3.  **Project Lead:** Define the specific "System Prompt" in **Phase 2.2** to ensure the LLM follows the JSON-only constraint.


