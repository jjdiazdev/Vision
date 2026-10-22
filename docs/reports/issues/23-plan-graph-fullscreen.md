# Issue Report: Full screen for the plan graph canvas

## Summary

This follows up on reports 21 and 22. The user asked to view only the graph's box, meaning the
status legend, the controls and the canvas, in full screen. Everything that works today had to
keep working there: pan, zoom, moving each repo's graph, node details and live updates.

A button in the canvas's bottom-right corner, the `F` key, or `Esc` (to leave) now toggles full
screen for `.plan-graph-focus`, a new wrapper around the toolbar and the stage. It uses the
Fullscreen API. Where that is unavailable, a fixed overlay does the same job. The view refits on
entering and leaving.

## Files Changed

- `dashboard_app/app/templates/partials/_plan_graph.html`
  - New `.plan-graph-focus` wrapper.
  - The full-screen button, with `aria-pressed`, a dynamic label and a title showing the shortcut.
  - The "Fit" button's icon changes from `bi-arrows-fullscreen` to `bi-aspect-ratio`, so the two
    buttons can't be confused.
  - A window key handler.
  - A card class used while the overlay is open.
- `dashboard_app/app/static/js/plan_graph.js`
  - New state: `isFullscreen` and `pseudoFullscreen`.
  - New methods: `toggleFullscreen`, `setPseudo`, `onFullscreenChange` (refit plus a cross-edge
    redraw), `onKey` (`F`, and `Esc` closing the details first), and native/webkit helpers.
  - Listener cleanup and an exit from full screen in `destroy`.
- `dashboard_app/app/static/css/style.css`
  - Full-screen layout (`:fullscreen` and `.is-pseudo-fullscreen`): a solid background, a flex
    column, and the canvas filling the rest of the screen.
  - The overlay sits at z-index 30001.
  - The card drops `backdrop-filter`/`overflow` while it hosts the overlay.
  - Styles for the button.
  - The detail panel leaves room above the button.
- Docs: `domains/flows.md`, `domains/test_coverage.md`, `README.md`.

## Validation Performed

- The plan suites each pass in their own process: `test_plan_graph`, `test_plan_progress`,
  `test_plan_status` and `test_plan_import`.
- I tested in headless Chrome against the local preview (gunicorn + gevent, synthetic `acme-org`
  plan, 20 s simulator), using real CDP input events.
- **Native full screen:**
  - A click on the button made `document.fullscreenElement` equal `.plan-graph-focus`, and
    `isFullscreen` became true. The screenshot shows only the legend, the controls and the
    canvas, with the exit button bottom right.
  - Inside full screen, a header drag moved the Web group (from `{x:0,y:439}` to `{x:977,y:20}`)
    and clicking a node opened the detail panel.
  - No animations ran inside the focus area.
  - Exiting restored the 477 px canvas and kept the saved layout.
  - The `F` key entered full screen again.
- **Overlay fallback** (`fullscreenEnabled` and `webkitFullscreenEnabled` forced to false):
  - The first run showed the overlay trapped inside the card. The cause was the card's
    `backdrop-filter`, which creates a containing block for fixed descendants. I fixed it with
    the hosting class.
  - After the fix, the overlay covered the full 1600×857 viewport at z-index 30001, above the HUD.
  - Pan moved the view, a group drag moved Web, and there were 0 animations.
  - `Esc` closed the overlay and restored the canvas.
- Headless Chrome sizes native full screen at 800×544, so that screenshot is small. A real browser
  uses the whole screen with the same CSS.

## Known Limitations

- Toasts are not visible in native full screen: they live outside the full-screen element. The
  graph still updates live.
- The full-screen state is not remembered. The view always opens in normal mode.

## Follow-up Recommendations

- None needed. If toasts are wanted in full screen, the alerts container would have to move inside
  `.plan-graph-focus` while it is active.
