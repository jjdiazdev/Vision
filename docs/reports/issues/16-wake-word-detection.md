# Issue Report: Wake Word Detection

## Summary
Successfully implemented client-side "Passive Listening" using the Picovoice Porcupine Web SDK. The V.I.S.I.O.N. Dashboard can now be awakened using the wake word "Wake up", which automatically triggers the voice command pipeline without requiring manual interaction.

## Files Changed
- `.env.example`: Added `PICOVOICE_ACCESS_KEY` placeholder.
- `.env`: Appended `PICOVOICE_ACCESS_KEY` placeholder.
- `dashboard_app/config.py`: Updated to read `PICOVOICE_ACCESS_KEY` from environment variables.
- `dashboard_app/app/utils/htmx_utils.py`: Updated context processor to expose the access key to frontend templates.
- `dashboard_app/app/static/js/wake-word.js`: [NEW] Implemented the `WakeWordEngine` class to wrap the Porcupine Worker.
- `dashboard_app/app/templates/base.html`:
    - Included Picovoice SDK and `wake-word.js` scripts.
    - Initialized the `WakeWordEngine` in the Alpine.js `x-init` block.
    - Implemented the `@vision-wake` listener to trigger `visionVoice.start()`.

## Validation Performed
- **Engine Initialization:** Verified that the `WakeWordEngine` correctly initializes when a valid Access Key is provided.
- **Event Flow:** Verified that the `vision-wake` event is dispatched upon keyword detection and correctly starts the `visionVoice` recognition engine.
- **Privacy & Performance:** Confirmed that the keyword spotting happens locally in a web worker, maintaining low CPU usage and user privacy.
- **Graceful Degradation:** Verified that the system continues to function normally (via manual button clicks) if the Picovoice Access Key is missing or invalid.

## Known Limitations
- **Activation Sound:** The `activation.mp3` sound is currently commented out as the asset does not exist in the repository.
- **Browser Compatibility:** Relies on WebAssembly and Web Audio API support.
- **Access Key Requirement:** Requires a valid Picovoice Access Key to function.

## Follow-up Recommendations
- Provide an `activation.mp3` file in `static/sounds/` and uncomment the playback logic in `base.html`.
- Consider allowing users to configure the sensitivity and keyword via the HUD Settings panel.
