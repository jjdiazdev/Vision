# Reports — Historical Record (Append-Only)

- **`issues/`** — closing reports for completed roadmap items: what shipped, what was verified,
  what broke and how it was fixed. Never rewritten in place — a correction gets a new, later
  report. See `../skills/write-closing-report/SKILL.md` for the template.
- **`specs/`** — the flip side: the work-order spec written *before* each corresponding `issues/`
  report, one per completed Phase 1–6 roadmap item (`docs/reports/specs/01_infrastructure_containerization/`
  through `06_testing_optimization/`).

## Known numbering irregularities (left as-is, not renumbered)

- `12-hybrid-intelligence-strategy.md` and `12-web-speech-api-integration.md` both use the prefix
  `12`.
- There is no file numbered `17` — the sequence jumps from `16-wake-word-detection.md` to
  `18-notification-system.md`.
- `16-wake-word-detection.md` has no corresponding spec under `specs/` — it documents work
  (Picovoice wake-word detection) that was never represented in the roadmap/milestone templates.

Renumbering 10+ existing files to close these gaps was considered and rejected — it risks breaking
any existing external references for a purely cosmetic fix. New reports just continue from the
current highest number.
