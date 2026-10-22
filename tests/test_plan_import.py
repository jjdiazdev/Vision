import copy
import unittest
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from execution.plan_import import PlanSpecError, validate_plan_spec

VALID = {
    "name": "Week 43", "org": "acme-org", "target_date": "2026-10-29",
    "groups": [{"key": "API", "label": "Backend", "repo": "acme-org/api"},
               {"key": "WEB", "label": "Web", "repo": "acme-org/web"}],
    "nodes": [
        {"key": "apimain", "group": "API", "kind": "base", "label": "origin/main"},
        {"key": "B1", "group": "API", "issue": 10, "display_key": "B-01", "label": "Contract"},
        {"key": "B2", "group": "API", "issue": 11},
        {"key": "webmain", "group": "WEB", "kind": "base", "label": "origin/main"},
        {"key": "W1", "group": "WEB", "issue": 10},
    ],
    "edges": [
        {"from": "apimain", "to": "B1", "kind": "base"},
        {"from": "B1", "to": "B2", "kind": "stacked"},
        {"from": "webmain", "to": "W1", "kind": "base"},
        {"from": "B1", "to": "W1", "kind": "cross", "label": "contract"},
    ],
}


def _spec(mutate):
    spec = copy.deepcopy(VALID)
    mutate(spec)
    return spec


class TestValidatePlanSpec(unittest.TestCase):
    def assertRejected(self, spec, fragment):
        with self.assertRaises(PlanSpecError) as ctx:
            validate_plan_spec(spec)
        self.assertTrue(any(fragment in e for e in ctx.exception.errors), ctx.exception.errors)

    def test_valid_spec_is_normalized(self):
        spec = validate_plan_spec(VALID)
        self.assertEqual(spec["target_date"].isoformat(), "2026-10-29")
        b2 = next(n for n in spec["nodes"] if n["key"] == "B2")
        self.assertEqual(b2["repo"], "acme-org/api")
        self.assertEqual(len(spec["edges"]), 4)

    def test_same_issue_number_in_two_repos_is_fine(self):
        validate_plan_spec(VALID)  # B1 and W1 are both #10

    def test_cycle_is_rejected_with_its_path(self):
        spec = _spec(lambda s: s["edges"].append({"from": "B2", "to": "B1", "kind": "stacked"}))
        self.assertRejected(spec, "dependency cycle B1 -> B2 -> B1")

    def test_cross_repo_cycle_is_rejected(self):
        spec = _spec(lambda s: s["edges"].append({"from": "W1", "to": "B1", "kind": "cross"}))
        self.assertRejected(spec, "dependency cycle")

    def test_duplicate_key(self):
        self.assertRejected(_spec(lambda s: s["nodes"].append({"key": "B2", "group": "API", "issue": 99})),
                            "duplicate node 'B2'")

    def test_duplicate_issue_in_same_repo(self):
        self.assertRejected(_spec(lambda s: s["nodes"].append({"key": "B9", "group": "API", "issue": 11})),
                            "acme-org/api#11 is already node 'B2'")

    def test_unknown_edge_endpoint(self):
        self.assertRejected(_spec(lambda s: s["edges"].append({"from": "B2", "to": "ZZ", "kind": "stacked"})),
                            "unknown node(s) ZZ")

    def test_stacked_edge_cannot_cross_repos(self):
        self.assertRejected(_spec(lambda s: s["edges"].append({"from": "B2", "to": "W1", "kind": "stacked"})),
                            "crosses repositories")

    def test_repo_outside_org(self):
        self.assertRejected(_spec(lambda s: s["groups"][1].update(repo="other-org/web")), "outside org")

    def test_issue_node_needs_number(self):
        self.assertRejected(_spec(lambda s: s["nodes"][2].pop("issue")), "positive integer issue number")
        self.assertRejected(_spec(lambda s: s["nodes"][2].update(issue=True)), "positive integer issue number")

    def test_base_edge_must_start_at_base_node(self):
        self.assertRejected(_spec(lambda s: s["edges"].append({"from": "B1", "to": "B2", "kind": "base"})),
                            "must start at a base node")

    def test_bad_date_and_kind(self):
        self.assertRejected(_spec(lambda s: s.update(target_date="29/10/2026")), "target_date")
        self.assertRejected(_spec(lambda s: s["edges"].append({"from": "B1", "to": "B2", "kind": "depends"})), "edges[4].kind")

    def test_all_errors_reported_together(self):
        def mutate(s):
            s["name"] = ""
            s["nodes"][2]["group"] = "NOPE"
        with self.assertRaises(PlanSpecError) as ctx:
            validate_plan_spec(_spec(mutate))
        self.assertGreaterEqual(len(ctx.exception.errors), 2)


if __name__ == '__main__':
    unittest.main()
