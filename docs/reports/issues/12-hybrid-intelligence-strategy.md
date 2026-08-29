# Issue Report: Hybrid Intelligence Strategy (NVIDIA NIM Integration)

## Status
- **Date:** 2026-05-27
- **Author:** Gemini CLI (YOLO Mode)
- **Status:** COMPLETED

## Problem Statement
V.I.S.I.O.N. was previously limited to local hardware capabilities (Ollama). For complex tasks requiring high-reasoning power, a cloud-based high-performance model was needed, while maintaining system resilience and "Local-First" principles.

## Solution Implemented
Implemented a **Hybrid Intelligence Strategy** using the `LLMGateway` pattern.

### 1. LLMGateway (Backend)
- Created `orchestrator/gateway.py` to abstract LLM calls.
- Integrated **NVIDIA NIM** (Cloud) via the OpenAI-compatible API.
- Implemented **Automatic Fallback**: If a cloud request fails (timeout, connectivity, etc.), the system transparently reverts to the local **Ollama** instance.
- Refactored `Orchestrator` in `orchestrator/brain.py` to delegate all LLM communication to the gateway.

### 2. HUD Interface (Frontend)
- Added a "High Performance" toggle in a new **HUD Settings** panel.
- Used **Alpine.js** for state management and `localStorage` for persistence.
- Implemented **Header Injection**: All chat requests now include an `X-LLM-Backend` header (`cloud` or `local`) based on the toggle state.

### 3. Flask Integration
- Updated `/agent/chat` route to detect the `X-LLM-Backend` header and pass the preference to the Orchestrator.

## Components Updated
- `.env.example`: Added NVIDIA NIM configuration keys.
- `dashboard_app/requirements.txt`: Added `openai` library.
- `orchestrator/gateway.py`: [NEW] LLM abstraction layer.
- `orchestrator/brain.py`: Refactored core orchestration logic.
- `dashboard_app/app/main/routes.py`: Updated chat routing.
- `dashboard_app/app/templates/base.html`: HUD UI and Logic.
- `dashboard_app/app/static/css/style.css`: HUD Styles.

## Verification Results
- **HUD Toggle:** Verified persistence in `localStorage`.
- **Header Injection:** Verified `X-LLM-Backend` is sent with HTMX requests.
- **Fail-safe Logic:** The `LLMGateway` wraps cloud calls in a robust `try-except` block, ensuring zero-downtime by falling back to Ollama.
- **Model Routing:** Orchestrator correctly passes backend preference to the Gateway.

## Future Considerations
- **Task Complexity Routing:** Automatically choosing the backend based on intent analysis.
- **Cost/Token Tracking:** Monitoring cloud usage for the system-wide API key.
