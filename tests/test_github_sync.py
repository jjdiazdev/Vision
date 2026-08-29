import unittest
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from execution.github_sync import _compute_review_state
from dashboard_app.app.models import ReviewStateEnum


def _issue(pr_number=101, reviews=None, commits=None):
    """Builds a synthetic GraphQL issue payload with one closedByPullRequestsReferences
    node (matching pr_number), shaped like ISSUE_FIELDS_WITH_REVIEW's response."""
    ref = {"number": pr_number, "state": "OPEN"}
    if reviews is not None:
        ref["reviews"] = {"nodes": reviews}
    if commits is not None:
        ref["commits"] = {"nodes": commits}
    return {"closedByPullRequestsReferences": {"nodes": [ref]}}


def _review(login, state, submitted_at):
    return {"author": {"login": login}, "state": state, "submittedAt": submitted_at}


def _commit(committed_at):
    return {"commit": {"committedDate": committed_at}}


class TestComputeReviewState(unittest.TestCase):
    def test_outstanding_changes_requested_no_later_commit(self):
        issue = _issue(reviews=[_review("alice", "CHANGES_REQUESTED", "2026-08-01T00:00:00Z")], commits=[])
        self.assertEqual(_compute_review_state(issue, 101), ReviewStateEnum.CHANGES_REQUESTED)

    def test_commit_after_changes_requested_marks_applied(self):
        issue = _issue(
            reviews=[_review("alice", "CHANGES_REQUESTED", "2026-08-01T00:00:00Z")],
            commits=[_commit("2026-08-02T00:00:00Z")],
        )
        self.assertEqual(_compute_review_state(issue, 101), ReviewStateEnum.CHANGES_APPLIED)

    def test_commit_before_changes_requested_still_requested(self):
        issue = _issue(
            reviews=[_review("alice", "CHANGES_REQUESTED", "2026-08-02T00:00:00Z")],
            commits=[_commit("2026-08-01T00:00:00Z")],
        )
        self.assertEqual(_compute_review_state(issue, 101), ReviewStateEnum.CHANGES_REQUESTED)

    def test_same_author_later_approval_clears_state(self):
        issue = _issue(reviews=[
            _review("alice", "CHANGES_REQUESTED", "2026-08-01T00:00:00Z"),
            _review("alice", "APPROVED", "2026-08-02T00:00:00Z"),
        ], commits=[])
        self.assertIsNone(_compute_review_state(issue, 101))

    def test_second_reviewer_still_outstanding_wins(self):
        issue = _issue(reviews=[
            _review("alice", "CHANGES_REQUESTED", "2026-08-01T00:00:00Z"),
            _review("bob", "APPROVED", "2026-08-02T00:00:00Z"),
        ], commits=[])
        self.assertEqual(_compute_review_state(issue, 101), ReviewStateEnum.CHANGES_REQUESTED)

    def test_no_reviews(self):
        issue = _issue(reviews=[], commits=[])
        self.assertIsNone(_compute_review_state(issue, 101))

    def test_all_approved(self):
        issue = _issue(reviews=[_review("alice", "APPROVED", "2026-08-01T00:00:00Z")], commits=[])
        self.assertIsNone(_compute_review_state(issue, 101))

    def test_no_pr_number(self):
        issue = _issue(reviews=[_review("alice", "CHANGES_REQUESTED", "2026-08-01T00:00:00Z")])
        self.assertIsNone(_compute_review_state(issue, None))

    def test_no_matching_pr_ref(self):
        issue = _issue(pr_number=101, reviews=[_review("alice", "CHANGES_REQUESTED", "2026-08-01T00:00:00Z")])
        self.assertIsNone(_compute_review_state(issue, 999))

    def test_deleted_author_review_is_skipped(self):
        issue = _issue(reviews=[
            {"author": None, "state": "CHANGES_REQUESTED", "submittedAt": "2026-08-01T00:00:00Z"},
        ], commits=[])
        self.assertIsNone(_compute_review_state(issue, 101))


if __name__ == '__main__':
    unittest.main()
