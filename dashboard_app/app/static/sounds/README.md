# Sounds

Expected file: `toast-notification.mp3` — played once for every toast notification (see
`window.playToastSound()` in `dashboard_app/app/templates/base.html`, and
`docs/domains/flows.md` for the full list of what triggers a toast).

Not committed here — supply your own file locally or at deploy time. If missing, toasts still
display normally; the sound is silently skipped (`.catch(() => {})`).
