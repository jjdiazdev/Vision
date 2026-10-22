"""Pure helpers for implementation plans: progress math and the Mermaid graph source.

No Flask, no DB: callers pass plain dicts/values, so this is unit-testable on its own
(tests/test_plan_graph.py, tests/test_plan_progress.py).

The graph keeps the plan documents' notation -- `graph LR`, one graph per repo, `-->` from
the base branch, `==>` stacked, `-.->|label|` conditions -- and their status-color rule,
re-lit for the HUD's dark background. Status is also carried by a glyph on every node, so it
never depends on color alone.
"""

DONE_STATUSES = ("fusionada", "cerrada")
EXCLUDED_STATUSES = ("descartada",)

# Mirrors the --plan-* tokens in static/css/style.css (legend chips use those). Mermaid's
# classDef splits on commas, so translucent fills are 8-digit hex rather than rgba().
NODE_STYLES = {
    "sinpr": "fill:#0075ff24,stroke:#4d9bff,stroke-width:1.5px,color:#d6e7ff",
    "conpr": "fill:#d2992229,stroke:#e3b341,stroke-width:1.5px,color:#f6e3b0",
    "prbloq": "fill:#d2992229,stroke:#f85149,stroke-width:3px,color:#f6e3b0",
    "fusionada": "fill:#01b5741f,stroke:#01b574,stroke-width:2px,stroke-dasharray:6 3,color:#b9f0d8",
    "cerrada": "fill:#01b5744d,stroke:#01b574,stroke-width:2px,color:#e3fbef",
    "descartada": "fill:#a0aec014,stroke:#a0aec059,stroke-width:1px,stroke-dasharray:2 3,color:#a0aec0",
    "pendiente": "fill:#00000000,stroke:#a0aec0,stroke-width:1px,stroke-dasharray:1 3,color:#a0aec0",
    "base": "fill:#00000000,stroke:#a0aec080,stroke-width:1px,color:#a0aec0",
}

STATUS_GLYPHS = {
    "sinpr": "○",
    "conpr": "◐",
    "prbloq": "⚠",
    "fusionada": "✓",
    "cerrada": "✔",
    "descartada": "⊘",
    "pendiente": "…",
}

STATUS_NAMES = {
    "sinpr": "No PR",
    "conpr": "PR open",
    "prbloq": "PR needs attention",
    "fusionada": "Merged, issue open",
    "cerrada": "Closed",
    "descartada": "Not planned",
    "pendiente": "Not synced yet",
}

LABEL_MAX = 38


def plan_progress(statuses):
    """statuses: iterable of plan status values ('sinpr', ..., or None when never synced).
    Done = merged or closed (PM decision, 2026-10-22); not-planned leaves the denominator;
    a never-synced item counts as not done."""
    done = total = 0
    for status in statuses:
        if status in EXCLUDED_STATUSES:
            continue
        total += 1
        if status in DONE_STATUSES:
            done += 1
    return {"done": done, "total": total, "percent": round(done / total * 100) if total else 0}


def escape_label(text):
    """Make arbitrary text safe inside a Mermaid quoted label. Mermaid decodes `#name;` /
    `#code;` entities, so ';' is encoded first and markup characters become entities --
    nothing a plan or GitHub title contains can open a tag or end the label."""
    text = " ".join(str(text).split())
    text = text.replace(";", "#59;")
    for char, entity in (('"', "#quot;"), ("<", "#lt;"), (">", "#gt;"), ("&", "#amp;"),
                         ("[", "#91;"), ("]", "#93;"), ("|", "#124;"), ("`", "#96;")):
        text = text.replace(char, entity)
    return text


def _shorten(text, limit=LABEL_MAX):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def node_status(node):
    if node["kind"] == "base":
        return "base"
    return node.get("status") or "pendiente"


def node_label(node):
    if node["kind"] == "base":
        return escape_label(node.get("label") or node["key"])
    status = node_status(node)
    glyph = STATUS_GLYPHS[status]
    head = f'{glyph} {node.get("display_key") or node["key"]} · #{node["issue"]}'
    lines = [escape_label(head)]
    text = node.get("label") or node.get("title")
    if text:
        lines.append(escape_label(_shorten(text)))
    if node.get("pr_number") and status in ("conpr", "prbloq", "fusionada"):
        pr = f'PR #{node["pr_number"]}'
        if node.get("pr_is_draft") and status != "fusionada":
            pr += " · draft"
        if status == "prbloq":
            if node.get("ci") in ("FAILURE", "ERROR"):
                pr += " · CI failing"
            if node.get("review") == "CHANGES_REQUESTED":
                pr += " · changes requested"
        lines.append(escape_label(pr))
    return "<br/>".join(lines)


def edge_arrow(edge, parent_status):
    """Mermaid arrow for an edge inside one repo's graph, or None for a cross-repo edge (those
    are drawn by the client's overlay layer, see cross_edges). Once a parent is merged or closed
    its children start from main, so stacked and after-merge edges relax to `-->` -- what the plan
    documents' progress snapshots do by hand."""
    kind = edge["kind"]
    parent_done = parent_status in DONE_STATUSES
    if kind == "base":
        return "-->"
    if kind == "stacked":
        return "-->" if parent_done else "==>"
    if kind == "after_merge":
        if parent_done:
            return "-->"
        return f'-.->|{escape_label(edge.get("label") or "after merge")}|'
    return None


def node_ids(nodes):
    """Stable Mermaid ids for the whole plan (n0, n1, ... in plan order), shared by every group's
    graph so the client can map a rendered node back to its plan item."""
    return {node["key"]: f"n{idx}" for idx, node in enumerate(nodes)}


def build_group_mermaid(group_key, nodes, edges, ids):
    """One repo's graph: `graph LR` with only that group's nodes and its same-repo edges.

    Each repo is rendered as its own SVG so the viewer can move it as a block; a single Mermaid
    drawing cannot be split apart afterwards (cluster nodes are siblings, not children, of the
    cluster box). The group title lives in the panel's HTML header, not in the source."""
    members = [n for n in nodes if n["group"] == group_key]
    member_keys = {n["key"] for n in members}
    status_by_key = {n["key"]: node_status(n) for n in nodes}
    lines = ["graph LR"]
    for node in members:
        nid = ids[node["key"]]
        if node["kind"] == "base":
            lines.append(f'  {nid}(("{node_label(node)}"))')
        else:
            lines.append(f'  {nid}["{node_label(node)}"]')

    for edge in edges:
        if edge["from"] not in member_keys or edge["to"] not in member_keys:
            continue
        arrow = edge_arrow(edge, status_by_key.get(edge["from"]))
        if arrow is not None:
            lines.append(f"  {ids[edge['from']]} {arrow} {ids[edge['to']]}")

    for name, style in NODE_STYLES.items():
        lines.append(f"  classDef st_{name} {style}")
    by_status = {}
    for node in members:
        by_status.setdefault(status_by_key[node["key"]], []).append(ids[node["key"]])
    for status, member_ids in by_status.items():
        lines.append(f"  class {','.join(member_ids)} st_{status}")
    return "\n".join(lines)


def cross_edges(nodes, edges):
    """Edges between two repos' graphs, for the client overlay: [{from, to, label}] by node key.
    Any edge whose endpoints sit in different groups is included, whatever its kind."""
    group_by_key = {n["key"]: n["group"] for n in nodes}
    result = []
    for edge in edges:
        src, dst = group_by_key.get(edge["from"]), group_by_key.get(edge["to"])
        if src is not None and dst is not None and src != dst:
            result.append({"from": edge["from"], "to": edge["to"], "label": edge.get("label")})
    return result
