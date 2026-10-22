"""Validation for implementation-plan specs (the JSON an agent extracts from a plan .md).

Pure and DB-free: `validate_plan_spec(spec)` returns a normalized copy of the spec or raises
PlanSpecError listing every problem with its JSON path. Persisting is agent_actions.import_plan's
job. The extraction procedure (Markdown/Mermaid -> this JSON) lives in
docs/skills/import-plan/SKILL.md, deliberately outside the code: plan documents vary too much
in language and notation for a parser to stay reliable.

Spec shape:
    {
      "name": "Phase 2", "org": "acme-org",
      "target_date": "2026-10-29",            # optional, YYYY-MM-DD
      "source": "IMPLEMENTATION_ROADMAP.md",  # optional
      "groups": [{"key": "API", "label": "Backend", "repo": "acme-org/api"}],
      "nodes": [
        {"key": "apimain", "group": "API", "kind": "base", "label": "origin/main"},
        {"key": "B01", "group": "API", "issue": 414, "display_key": "B-01", "label": "Abilities"}
      ],
      "edges": [{"from": "apimain", "to": "B01", "kind": "base"},
                {"from": "B01", "to": "W01", "kind": "cross", "label": "contract"}]
    }

A node's repo defaults to its group's repo; an issue node may override it with "repo".
"""

import re
from datetime import date

NODE_KINDS = ("issue", "base")
EDGE_KINDS = ("base", "stacked", "after_merge", "cross")
# Edges that model branching inside one repository. A PR has one base branch in its own repo,
# so these can never cross repositories; cross-repo dependencies are always "cross".
SAME_REPO_EDGE_KINDS = ("base", "stacked", "after_merge")

KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,49}$")
REPO_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$")


class PlanSpecError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Invalid plan spec:\n" + "\n".join(f"  - {e}" for e in errors))


def _text(value, limit):
    return isinstance(value, str) and 0 < len(value.strip()) <= limit


def _find_cycle(keys, edges):
    """Returns one cycle as a list of keys, or None. Iterative DFS (plans can be long chains)."""
    adjacency = {k: [] for k in keys}
    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])
    WHITE, GREY, BLACK = 0, 1, 2
    color = {k: WHITE for k in keys}
    parent = {}
    for start in keys:
        if color[start] != WHITE:
            continue
        stack = [(start, iter(adjacency[start]))]
        color[start] = GREY
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                color[node] = BLACK
                stack.pop()
            elif color[child] == GREY:
                cycle = [child, node]
                while cycle[-1] != child:
                    cycle.append(parent[cycle[-1]])
                return list(reversed(cycle))
            elif color[child] == WHITE:
                parent[child] = node
                color[child] = GREY
                stack.append((child, iter(adjacency[child])))
    return None


def validate_plan_spec(spec):
    errors = []
    if not isinstance(spec, dict):
        raise PlanSpecError(["spec: must be a JSON object"])

    if not _text(spec.get("name"), 200):
        errors.append("name: required, 1-200 characters")
    org = spec.get("org")
    if not isinstance(org, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", org or ""):
        errors.append("org: required GitHub organization login")
        org = None

    target_date = spec.get("target_date")
    if target_date is not None:
        try:
            target_date = date.fromisoformat(target_date)
        except (TypeError, ValueError):
            errors.append("target_date: must be YYYY-MM-DD")
            target_date = None

    source = spec.get("source")
    if source is not None and not _text(source, 255):
        errors.append("source: must be 1-255 characters")

    groups = {}
    for idx, group in enumerate(spec.get("groups") or []):
        path = f"groups[{idx}]"
        if not isinstance(group, dict):
            errors.append(f"{path}: must be an object")
            continue
        key, repo = group.get("key"), group.get("repo")
        if not isinstance(key, str) or not KEY_PATTERN.match(key):
            errors.append(f"{path}.key: must match {KEY_PATTERN.pattern}")
            continue
        if key in groups:
            errors.append(f"{path}.key: duplicate group '{key}'")
            continue
        if not isinstance(repo, str) or not REPO_PATTERN.match(repo):
            errors.append(f"{path}.repo: must be 'owner/name'")
        elif org and repo.split("/")[0].lower() != org.lower():
            errors.append(f"{path}.repo: '{repo}' is outside org '{org}'")
        groups[key] = {"key": key, "repo": repo, "label": group.get("label") or key}
    if not groups:
        errors.append("groups: at least one group is required")

    nodes = {}
    issues_seen = {}
    for idx, node in enumerate(spec.get("nodes") or []):
        path = f"nodes[{idx}]"
        if not isinstance(node, dict):
            errors.append(f"{path}: must be an object")
            continue
        key = node.get("key")
        if not isinstance(key, str) or not KEY_PATTERN.match(key):
            errors.append(f"{path}.key: must match {KEY_PATTERN.pattern}")
            continue
        if key in nodes:
            errors.append(f"{path}.key: duplicate node '{key}'")
            continue
        group = groups.get(node.get("group"))
        if not group:
            errors.append(f"{path}.group: unknown group '{node.get('group')}'")
            continue
        kind = node.get("kind", "issue")
        if kind not in NODE_KINDS:
            errors.append(f"{path}.kind: must be one of {', '.join(NODE_KINDS)}")
            continue
        repo = node.get("repo") or group["repo"]
        if not isinstance(repo, str) or not REPO_PATTERN.match(repo):
            errors.append(f"{path}.repo: must be 'owner/name'")
            continue
        if org and repo.split("/")[0].lower() != org.lower():
            errors.append(f"{path}.repo: '{repo}' is outside org '{org}'")
        label = node.get("label")
        if label is not None and not _text(label, 200):
            errors.append(f"{path}.label: must be 1-200 characters")
        display_key = node.get("display_key")
        if display_key is not None and not _text(display_key, 50):
            errors.append(f"{path}.display_key: must be 1-50 characters")

        issue = node.get("issue")
        if kind == "issue":
            if isinstance(issue, bool) or not isinstance(issue, int) or issue <= 0:
                errors.append(f"{path}.issue: issue nodes need a positive integer issue number")
                continue
            seen = issues_seen.get((repo.lower(), issue))
            if seen:
                errors.append(f"{path}.issue: {repo}#{issue} is already node '{seen}'")
                continue
            issues_seen[(repo.lower(), issue)] = key
        elif issue is not None:
            errors.append(f"{path}.issue: base nodes have no issue")
            continue

        nodes[key] = {
            "key": key, "group": group["key"], "kind": kind, "repo": repo,
            "issue": issue if kind == "issue" else None,
            "display_key": display_key, "label": label,
        }
    if not any(n["kind"] == "issue" for n in nodes.values()):
        errors.append("nodes: at least one issue node is required")

    edges = []
    seen_edges = set()
    for idx, edge in enumerate(spec.get("edges") or []):
        path = f"edges[{idx}]"
        if not isinstance(edge, dict):
            errors.append(f"{path}: must be an object")
            continue
        src, dst, kind = edge.get("from"), edge.get("to"), edge.get("kind")
        if src not in nodes or dst not in nodes:
            missing = [k for k in (src, dst) if k not in nodes]
            errors.append(f"{path}: unknown node(s) {', '.join(map(str, missing))}")
            continue
        if src == dst:
            errors.append(f"{path}: self-loop on '{src}'")
            continue
        if kind not in EDGE_KINDS:
            errors.append(f"{path}.kind: must be one of {', '.join(EDGE_KINDS)}")
            continue
        if kind in SAME_REPO_EDGE_KINDS and nodes[src]["repo"].lower() != nodes[dst]["repo"].lower():
            errors.append(f"{path}: '{kind}' edge {src} -> {dst} crosses repositories; use 'cross'")
            continue
        if kind == "base" and nodes[src]["kind"] != "base":
            errors.append(f"{path}: 'base' edges must start at a base node, '{src}' is an issue")
            continue
        if kind != "base" and nodes[src]["kind"] == "base":
            errors.append(f"{path}: an edge from base node '{src}' must have kind 'base'")
            continue
        label = edge.get("label")
        if label is not None and not _text(label, 100):
            errors.append(f"{path}.label: must be 1-100 characters")
            continue
        if (src, dst, kind) in seen_edges:
            errors.append(f"{path}: duplicate edge {src} -> {dst} ({kind})")
            continue
        seen_edges.add((src, dst, kind))
        edges.append({"from": src, "to": dst, "kind": kind, "label": label})

    if not errors:
        cycle = _find_cycle(list(nodes), edges)
        if cycle:
            errors.append("edges: dependency cycle " + " -> ".join(cycle))

    if errors:
        raise PlanSpecError(errors)

    return {
        "name": spec["name"].strip(), "org": org, "target_date": target_date, "source": source,
        "groups": list(groups.values()), "nodes": list(nodes.values()), "edges": edges,
    }
