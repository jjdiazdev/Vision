import unittest
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from execution.github_sync import GitHubWriteAttempt, assert_read_only, ISSUES_QUERY, ISSUE_FIELDS_WITH_REVIEW, RATE_LIMIT_QUERY
from execution.plan_sync import PLAN_ITEM_FIELDS, compute_plan_snapshot, compute_plan_status, select_pr
from dashboard_app.app.models import PlanStatusEnum

REPO = "acme-org/api"


def _pr(number, state="OPEN", merged=False, draft=False, ci=None, review=None, repo=REPO):
    commit = {"statusCheckRollup": {"state": ci} if ci else None}
    return {"number": number, "state": state, "merged": merged, "isDraft": draft, "reviewDecision": review,
            "repository": {"nameWithOwner": repo}, "commits": {"nodes": [{"commit": commit}]}}


def _issue(state="OPEN", reason=None, closing=(), referencing=()):
    return {
        "number": 7, "title": "Do the thing", "state": state, "stateReason": reason,
        "closedByPullRequestsReferences": {"nodes": list(closing)},
        "timelineItems": {"nodes": [{"source": pr} for pr in referencing] + [{"source": {}}, {}]},
    }


class TestComputePlanStatus(unittest.TestCase):
    def test_open_issue_without_pr_is_sinpr(self):
        self.assertEqual(compute_plan_status(_issue(), REPO), PlanStatusEnum.NO_PR)

    def test_open_pr_with_green_ci_is_conpr(self):
        self.assertEqual(compute_plan_status(_issue(closing=[_pr(10, ci="SUCCESS")]), REPO), PlanStatusEnum.PR_OPEN)

    def test_draft_pr_is_conpr_and_flagged(self):
        snap = compute_plan_snapshot(_issue(closing=[_pr(10, draft=True)]), REPO)
        self.assertEqual(snap["plan_status"], PlanStatusEnum.PR_OPEN)
        self.assertTrue(snap["pr_is_draft"])

    def test_red_ci_is_prbloq(self):
        for ci in ("FAILURE", "ERROR"):
            self.assertEqual(compute_plan_status(_issue(closing=[_pr(10, ci=ci)]), REPO), PlanStatusEnum.PR_BLOCKED)

    def test_changes_requested_is_prbloq(self):
        issue = _issue(closing=[_pr(10, ci="SUCCESS", review="CHANGES_REQUESTED")])
        self.assertEqual(compute_plan_status(issue, REPO), PlanStatusEnum.PR_BLOCKED)

    def test_unreadable_ci_never_counts_as_failing(self):
        snap = compute_plan_snapshot(_issue(closing=[_pr(10, ci=None)]), REPO)
        self.assertEqual(snap["plan_status"], PlanStatusEnum.PR_OPEN)
        self.assertIsNone(snap["pr_ci_state"])

    def test_merged_pr_with_open_issue_is_fusionada(self):
        snap = compute_plan_snapshot(_issue(closing=[_pr(10, state="MERGED", merged=True)]), REPO)
        self.assertEqual(snap["plan_status"], PlanStatusEnum.MERGED)
        self.assertEqual(snap["pr_state"], "MERGED")

    def test_refs_only_pr_is_found_through_cross_reference(self):
        issue = _issue(referencing=[_pr(11, state="MERGED", merged=True)])
        self.assertEqual(compute_plan_status(issue, REPO), PlanStatusEnum.MERGED)

    def test_closed_issue_is_cerrada_even_without_pr(self):
        self.assertEqual(compute_plan_status(_issue(state="CLOSED", reason="COMPLETED"), REPO), PlanStatusEnum.CLOSED)

    def test_not_planned_and_duplicate_are_descartada(self):
        for reason in ("NOT_PLANNED", "DUPLICATE"):
            self.assertEqual(compute_plan_status(_issue(state="CLOSED", reason=reason), REPO), PlanStatusEnum.NOT_PLANNED)

    def test_only_abandoned_pr_is_sinpr(self):
        issue = _issue(referencing=[_pr(12, state="CLOSED")])
        snap = compute_plan_snapshot(issue, REPO)
        self.assertEqual(snap["plan_status"], PlanStatusEnum.NO_PR)
        self.assertIsNone(snap["pr_number"])

    def test_open_pr_wins_over_merged_one(self):
        issue = _issue(closing=[_pr(10, state="MERGED", merged=True), _pr(13, ci="FAILURE")])
        snap = compute_plan_snapshot(issue, REPO)
        self.assertEqual(snap["pr_number"], 13)
        self.assertEqual(snap["plan_status"], PlanStatusEnum.PR_BLOCKED)

    def test_prs_from_other_repos_are_ignored(self):
        issue = _issue(referencing=[_pr(20, repo="acme-org/web")])
        self.assertEqual(compute_plan_status(issue, REPO), PlanStatusEnum.NO_PR)

    def test_repo_match_is_case_insensitive(self):
        issue = _issue(closing=[_pr(10, repo="Acme-Org/API")])
        self.assertEqual(compute_plan_status(issue, REPO), PlanStatusEnum.PR_OPEN)

    def test_select_pr_prefers_highest_open_number(self):
        self.assertEqual(select_pr([_pr(3), _pr(9), _pr(5, state="MERGED", merged=True)])["number"], 9)
        self.assertIsNone(select_pr([_pr(3, state="CLOSED")]))


class TestReadOnlyGuard(unittest.TestCase):
    def test_project_queries_pass(self):
        for query in (ISSUES_QUERY, RATE_LIMIT_QUERY, f"query {{ repository(owner: \"a\", name: \"b\") {{ i0: issue(number: 1) {{ {PLAN_ITEM_FIELDS} }} }} }}",
                      f"{{ viewer {{ login }} }} {ISSUE_FIELDS_WITH_REVIEW and ''}"):
            assert_read_only(query)

    def test_mutation_is_rejected(self):
        with self.assertRaises(GitHubWriteAttempt):
            assert_read_only('mutation { closeIssue(input: {issueId: "x"}) { clientMutationId } }')

    def test_named_mutation_after_query_is_rejected(self):
        with self.assertRaises(GitHubWriteAttempt):
            assert_read_only('query A { viewer { login } }\nmutation B { addComment(input: {}) { clientMutationId } }')

    def test_subscription_is_rejected(self):
        with self.assertRaises(GitHubWriteAttempt):
            assert_read_only("subscription { x }")

    def test_word_mutation_inside_strings_or_fields_is_allowed(self):
        assert_read_only('query { search(query: "mutation testing", type: ISSUE, first: 1) { issueCount } }')
        assert_read_only('# mutation in a comment\nquery { viewer { login } }')
        assert_read_only('query { repository(owner: "a", name: "mutation") { mutationTitle: name } }')


if __name__ == '__main__':
    unittest.main()
