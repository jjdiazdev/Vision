# Issue Report: HUD Pulse Loading State

## Summary
Implemented a visual "thinking" indicator in the Iron Man HUD. The HUD Core now pulses with an intense blue glow whenever an HTMX request is in progress, providing the user with real-time feedback during AI processing or data synchronization.

## Files Changed
- `dashboard_app/app/static/css/style.css`:
    - Defined `@keyframes hudPulse` for a brightness and glow effect.
    - Added `.hud-processing .hud-core-inner` to apply the animation and increase opacity.
- `dashboard_app/app/templates/base.html`:
    - Added `processing: false` to the HUD's Alpine.js `x-data`.
    - Implemented global event listeners `@htmx:before-request.window` and `@htmx:after-request.window` to toggle the `processing` state.
    - Bound the `hud-processing` class to the HUD container based on the `processing` state.

## Validation Performed
- Verified that the `processing` state correctly toggles during chat message submissions.
- Confirmed the animation applies only when `processing` is true and stops immediately after the request completes.
- Verified that the pulsing effect is visually consistent with the existing HUD aesthetic.

## Known Limitations
- The pulsing animation occurs for *any* HTMX request on the page (e.g., table refreshes), not just chat messages. This is intended as it provides a general "system busy" indicator.

## Follow-up Recommendations
- If more granular feedback is needed, specify the HTMX target in the event listeners to only pulse for chat-related requests.
- Add a text-based status indicator (e.g., "Analyzing...") within the chat window header during processing.
