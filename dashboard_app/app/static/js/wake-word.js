/**
 * WakeWordEngine: A wrapper for Picovoice Porcupine Web SDK
 * for the V.I.S.I.O.N. Dashboard.
 */
class WakeWordEngine {
    constructor(accessKey, keyword = 'Wake up') {
        this.accessKey = accessKey;
        this.keyword = keyword;
        this.porcupine = null;
        this.isListening = false;
    }

    async init() {
        if (!this.accessKey) {
            console.warn('[WakeWordEngine] Picovoice Access Key missing. Passive listening disabled.');
            return;
        }

        try {
            // Initialize Porcupine Worker
            // We use 'Wake up' as the keyword. In a real scenario, this would be a built-in or custom .ppn
            this.porcupine = await PorcupineWeb.PorcupineWorker.create(
                this.accessKey,
                this.keyword,
                { sensitivity: 0.7 }
            );

            this.porcupine.onmessage = (msg) => {
                if (msg.data.command === 'ppn-keyword') {
                    console.log("[WakeWordEngine] Wake word detected!");
                    this.dispatch('vision-wake');
                }
            };

            await WebVoiceProcessor.WebVoiceProcessor.subscribe(this.porcupine);
            this.isListening = true;
            console.log("[WakeWordEngine] V.I.S.I.O.N. is now listening passively for: " + this.keyword);
        } catch (err) {
            console.error("[WakeWordEngine] Initialization failed:", err);
        }
    }

    async stop() {
        if (!this.porcupine) return;
        try {
            await WebVoiceProcessor.WebVoiceProcessor.unsubscribe(this.porcupine);
            this.porcupine.terminate();
            this.isListening = false;
            console.log("[WakeWordEngine] Passive listening stopped.");
        } catch (err) {
            console.error("[WakeWordEngine] Failed to stop:", err);
        }
    }

    dispatch(name, detail = {}) {
        const event = new CustomEvent(name, { detail, bubbles: true });
        window.dispatchEvent(event);
    }
}
