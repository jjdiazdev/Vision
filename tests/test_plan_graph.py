import unittest
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from dashboard_app.app.utils.plan_graph import (build_group_mermaid, cross_edges, edge_arrow, escape_label,
                                                node_ids, plan_progress)


def _node(key, status=None, kind="issue", group="API", **extra):
    node = {"key": key, "kind": kind, "group": group, "issue": None if kind == "base" else 1,
            "display_key": None, "label": key, "title": None, "status": status,
            "pr_number": None, "pr_is_draft": None, "ci": None, "review": None}
    node.update(extra)
    return node


class TestEdges(unittest.TestCase):
    def test_stacked_edge_relaxes_once_parent_is_done(self):
        edge = {"kind": "stacked"}
        self.assertEqual(edge_arrow(edge, "conpr"), "==>")
        self.assertEqual(edge_arrow(edge, "fusionada"), "-->")
        self.assertEqual(edge_arrow(edge, "cerrada"), "-->")

    def test_after_merge_edge(self):
        self.assertEqual(edge_arrow({"kind": "after_merge", "label": "merged"}, "sinpr"), "-.->|merged|")
        self.assertEqual(edge_arrow({"kind": "after_merge"}, "cerrada"), "-->")

    def test_cross_edges_are_never_drawn_inside_a_group(self):
        self.assertIsNone(edge_arrow({"kind": "cross", "label": "contract"}, "sinpr"))


class TestGroupMermaid(unittest.TestCase):
    def setUp(self):
        self.nodes = [
            _node("main", kind="base", label="origin/main"),
            _node("B1", "fusionada", display_key="B-01", pr_number=44),
            _node("B2", "prbloq", pr_number=45, ci="FAILURE"),
            _node("B3"),
            _node("webmain", kind="base", group="WEB", label="origin/main"),
            _node("W1", "conpr", group="WEB"),
        ]
        self.edges = [{"from": "main", "to": "B1", "kind": "base", "label": None},
                      {"from": "B1", "to": "B2", "kind": "stacked", "label": None},
                      {"from": "B2", "to": "B3", "kind": "stacked", "label": None},
                      {"from": "webmain", "to": "W1", "kind": "base", "label": None},
                      {"from": "B2", "to": "W1", "kind": "cross", "label": "contract"}]
        self.ids = node_ids(self.nodes)

    def test_shape(self):
        src = build_group_mermaid("API", self.nodes, self.edges, self.ids)
        self.assertTrue(src.startswith("graph LR"))
        self.assertNotIn("subgraph", src)
        self.assertIn('n0(("origin/main"))', src)
        self.assertIn("n0 --> n1", src)
        self.assertIn("n1 --> n2", src)   # parent merged: no longer stacked
        self.assertIn("n2 ==> n3", src)   # parent open: still stacked

    def test_only_its_own_nodes_and_no_cross_edges(self):
        api = build_group_mermaid("API", self.nodes, self.edges, self.ids)
        web = build_group_mermaid("WEB", self.nodes, self.edges, self.ids)
        self.assertNotIn("n5", api)
        self.assertNotIn("n1", web)
        self.assertNotIn("contract", api + web)
        self.assertIn("n4 --> n5", web)   # ids stay plan-wide, not per group

    def test_cross_edges_listed_for_the_overlay(self):
        self.assertEqual(cross_edges(self.nodes, self.edges), [{"from": "B2", "to": "W1", "label": "contract"}])

    def test_status_classes_and_glyphs(self):
        src = build_group_mermaid("API", self.nodes, self.edges, self.ids)
        self.assertIn("class n1 st_fusionada", src)
        self.assertIn("class n2 st_prbloq", src)
        self.assertIn("class n3 st_pendiente", src)
        self.assertIn("class n0 st_base", src)
        self.assertIn("✓ B-01 · #1", src)
        self.assertIn("PR #45 · CI failing", src)

    def test_untrusted_text_cannot_break_out(self):
        nodes = [_node("B1", "sinpr", label='x"] --> evil[<img src=x onerror=alert(1)>]; |y|')]
        src = build_group_mermaid("API", nodes, [], node_ids(nodes))
        label_line = next(l for l in src.splitlines() if l.strip().startswith("n0["))
        self.assertEqual(label_line.count('"'), 2)
        for bad in ("<img", "]", "|y|"):
            self.assertNotIn(bad, label_line[label_line.index('"') + 1:label_line.rindex('"')])

    def test_escape_label_encodes_semicolon_first(self):
        self.assertEqual(escape_label('a;"b'), "a#59;#quot;b")


class TestPlanProgress(unittest.TestCase):
    def test_merged_and_closed_count_as_done(self):
        self.assertEqual(plan_progress(["fusionada", "cerrada", "conpr", "sinpr"]),
                         {"done": 2, "total": 4, "percent": 50})

    def test_not_planned_leaves_the_denominator(self):
        self.assertEqual(plan_progress(["cerrada", "descartada"]), {"done": 1, "total": 1, "percent": 100})

    def test_never_synced_counts_as_not_done(self):
        self.assertEqual(plan_progress([None, "cerrada", None]), {"done": 1, "total": 3, "percent": 33})

    def test_empty(self):
        self.assertEqual(plan_progress([]), {"done": 0, "total": 0, "percent": 0})


if __name__ == '__main__':
    unittest.main()
