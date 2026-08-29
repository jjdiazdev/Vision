/**
 * VisionVoice: A wrapper for the Web Speech API (webkitSpeechRecognition)
 * for the V.I.S.I.O.N. Dashboard.
 */
class VisionVoice {
    constructor() {
        this.recognition = null;
        this.isRecording = false;
        this.silenceTimer = null;
        this.silenceThreshold = 2000; // 2 seconds of silence before auto-stop
        this.init();
    }

    init() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.error('[VisionVoice] Speech Recognition API not supported in this browser.');
            this.unsupported = true;
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true; // Stay active to allow multi-phrase commands
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            console.log('[VisionVoice] Recognition started');
            this.isRecording = true;
            this.dispatch('voice-start');
            this.resetSilenceTimer();
        };

        this.recognition.onspeechstart = () => {
            console.log('[VisionVoice] Speech detected...');
            this.resetSilenceTimer();
        };

        this.recognition.onresult = (event) => {
            this.resetSilenceTimer();
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            console.log('[VisionVoice] Result:', finalTranscript || interimTranscript);
            this.dispatch('voice-result', {
                final: finalTranscript,
                interim: interimTranscript
            });

            if (finalTranscript) {
                this.dispatch('voice-transcript', { text: finalTranscript });
            }
        };

        this.recognition.onerror = (event) => {
            console.error('[VisionVoice] Recognition error:', event.error);
            this.isRecording = false;
            this.clearSilenceTimer();
            this.dispatch('voice-error', { error: event.error });
        };

        this.recognition.onend = () => {
            console.log('[VisionVoice] Recognition ended');
            this.isRecording = false;
            this.clearSilenceTimer();
            this.dispatch('voice-end');
        };
    }

    resetSilenceTimer() {
        this.clearSilenceTimer();
        if (this.isRecording) {
            this.silenceTimer = setTimeout(() => {
                console.log('[VisionVoice] Silence detected, stopping...');
                this.stop();
            }, this.silenceThreshold);
        }
    }

    clearSilenceTimer() {
        if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
        }
    }

    start(customThreshold = null) {
        if (!this.recognition) return;
        
        // Ensure we clear everything before a new session
        this.clearSilenceTimer();
        this.isRecording = false; 

        if (customThreshold) {
            console.log(`[VisionVoice] Starting with custom threshold: ${customThreshold}ms`);
            this.silenceThreshold = customThreshold;
        } else {
            this.silenceThreshold = 2000; // Reset to default 2s
        }

        try {
            this.recognition.start();
        } catch (e) {
            console.warn('[VisionVoice] Recognition already started or failed to start. Attempting to stop and restart...', e);
            this.recognition.stop();
            setTimeout(() => {
                try { this.recognition.start(); } catch(err) { console.error('[VisionVoice] Failed to restart:', err); }
            }, 300);
        }
    }

    stop() {
        if (!this.recognition) return;
        this.recognition.stop();
    }

    toggle() {
        if (this.unsupported) {
            if (window.addAlert) {
                window.addAlert('Speech Recognition is not supported in this browser. Please use Chrome or Edge.', 'error');
            } else {
                alert('Speech Recognition is not supported in this browser. Please use Chrome or Edge.');
            }
            return;
        }
        if (this.isRecording) {
            this.stop();
        } else {
            this.start();
        }
    }

    dispatch(name, detail = {}) {
        const event = new CustomEvent(name, { detail, bubbles: true });
        window.dispatchEvent(event);
    }
}

// Export to global scope for Alpine.js
window.visionVoice = new VisionVoice();
