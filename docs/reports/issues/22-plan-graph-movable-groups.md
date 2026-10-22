# Issue Report: Plan graph without animation, with movable repo groups

## Summary

This follows up on the plan graph (report 21, ADR 0003) after a local review. The user asked for
two changes:

- No animation at all in the graph view. The colors and glyphs are enough.
- Being able to move each repo's graph (backend, web, mobile) as a block on the canvas.

Moving a group required changing how the graph is rendered. Mermaid draws a subgraph's nodes as
siblings of its cluster box, so one SVG cannot be split after rendering. Each repo is now rendered
as its own Mermaid SVG inside a draggable panel. Edges between repos are drawn on a client overlay
that follows the panels. Layouts are kept per browser and per plan.

## Files Changed

- `dashboard_app/app/utils/plan_graph.py`
  - `build_mermaid` is replaced by `node_ids`, `build_group_mermaid` (one repo, same-repo edges
    only, no `subgraph`) and `cross_edges`.
  - `edge_arrow` no longer takes `show_cross`.
- `dashboard_app/app/main/routes.py`
  - `api_plan_graph` returns `groups[].mermaid` and `cross_edges`.
  - The `?cross` parameter is removed.
- `dashboard_app/app/static/js/plan_graph.js` (rewritten)
  - One panel per group, created imperatively.
  - Pointer drag on the header, and arrow-key moves when it has focus.
  - Positions saved in localStorage, with Reset layout.
  - Overlay layer for cross-repo edges, measured against the rendered panel scale.
  - The status-change flash is removed.
- `dashboard_app/app/templates/partials/_plan_graph.html`
  - Adds the overlay SVG with its arrow marker and the Reset layout button.
  - Removes the side panel's `x-transition`.
  - Adds `data-animated` to opt out of the entrance animation.
- `dashboard_app/app/static/css/style.css`
  - Removes the node sweep keyframes, the progress bar transition and shine in the graph, and the
    view switch's hover transition.
  - Adds panel, handle, overlay and reset styles.
- `tests/test_plan_graph.py` and `tests/test_plan_progress.py` are adapted to the per-group shape.
- Docs: `domains/flows.md`, `domains/api_endpoints.md`, `domains/test_coverage.md`,
  `memory/knowledge_base.md`, `README.md`.

## Validation Performed

- Plan suites, each run in its own process, all OK:
  - `python -m unittest tests.test_plan_graph`: 13 tests.
  - `tests.test_plan_progress`: 9 tests.
  - `tests.test_plan_status`: 20 tests.
  - `tests.test_plan_import`: 13 tests.
- Headless Chrome against the local preview, which runs gunicorn + gevent with a synthetic
  `acme-org` plan and the 20 s status simulator:
  - Real mouse drags through CDP moved Web and Mobile to a right-hand column. The saved positions
    were `{"API":{"x":0,"y":0},"WEB":{"x":1056,"y":0},"MOB":{"x":1056,"y":651}}` and 6 cross
    paths were drawn.
  - After a reload the layout was kept.
  - The first version anchored cross edges wrongly after a reload: it measured with `view.k`
    while the browser had painted a different transform. This was fixed by measuring against the
    rendered panel scale. A redraw now produces the identical path ("stable").
  - Arrow keys moved a panel (Shift+Right gave 80 px).
  - Reset layout cleared the stored key and stacked the panels again.
  - `document.getAnimations()` inside the graph card returned 0 after a refresh. It had returned 1
    before `data-animated` was added (the `fadeInSlideUp` entrance animation).

## Known Limitations

- Cross-repo edges are curves from node to node. They can pass over other nodes of the source
  panel. They are hidden by default.
- Layouts live in each viewer's browser. They are not shared across the team, not synced across
  devices, and lost if site data is cleared (by decision, 2026-10-22).
- Panels can overlap if the viewer drags them onto each other. There is no snapping or collision
  handling.

## Follow-up Recommendations

- If the team wants one shared layout, store it on the Plan (a JSON column and a POST route).
