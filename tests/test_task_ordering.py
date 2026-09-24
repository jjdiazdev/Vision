"""Tests for sort_tasks() in dashboard_app/app/main/routes.py.

DB-free and create_app-free (stub task objects), so this is exempt from the two-files-one-
process shared-`db` conflict documented in docs/domains/test_coverage.md.
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from dashboard_app.app.models import StatusEnum
from dashboard_app.app.main.routes import TASK_STATUS_ORDER, sort_tasks

BASE = datetime(2026, 9, 1, 12, 0)


class T:
    """Minimal stand-in for a Task row: sort_tasks only reads these five attributes."""
    def __init__(self, tid, status=StatusEnum.TODO, github_created_at=None,
                 created_at=None, github_issue_number=None):
        self.id = tid
        self.status = status
        self.github_created_at = github_created_at
        self.created_at = created_at if created_at is not None else BASE
        self.github_issue_number = github_issue_number

    def __repr__(self):
        return f"T({self.id})"


def ids(tasks):
    return [t.id for t in tasks]


class TestStatusBuckets(unittest.TestCase):
    def test_bucket_order_is_unchanged(self):
        tasks = [
            T(1, StatusEnum.BLOCKED), T(2, StatusEnum.DONE), T(3, StatusEnum.REPEAT_DAILY),
            T(4, StatusEnum.TODO), T(5, StatusEnum.IN_PROGRESS), T(6, StatusEnum.TESTING),
        ]
        self.assertEqual(ids(sort_tasks(tasks)), [6, 5, 4, 3, 2, 1])

    def test_unknown_status_sorts_last(self):
        odd = T(9, status=None)
        self.assertEqual(ids(sort_tasks([odd, T(1, StatusEnum.BLOCKED)])), [1, 9])
        self.assertEqual(TASK_STATUS_ORDER.get(None, 99), 99)


class TestRecencyWithinBucket(unittest.TestCase):
    def test_newest_github_issue_first(self):
        old = T(1, github_created_at=BASE - timedelta(days=10), github_issue_number=1)
        mid = T(2, github_created_at=BASE - timedelta(days=5), github_issue_number=2)
        new = T(3, github_created_at=BASE, github_issue_number=3)
        self.assertEqual(ids(sort_tasks([old, new, mid])), [3, 2, 1])

    def test_recency_applies_per_bucket_not_globally(self):
        # A very new Done task must still sit below an ancient Todo one.
        ancient_todo = T(1, StatusEnum.TODO, github_created_at=BASE - timedelta(days=99))
        fresh_done = T(2, StatusEnum.DONE, github_created_at=BASE)
        self.assertEqual(ids(sort_tasks([fresh_done, ancient_todo])), [1, 2])

    def test_same_second_tie_broken_by_higher_issue_number(self):
        # GitHub's createdAt has 1-second resolution, so burst-created issues collide.
        a = T(1, github_created_at=BASE, github_issue_number=10)
        b = T(2, github_created_at=BASE, github_issue_number=42)
        c = T(3, github_created_at=BASE, github_issue_number=7)
        self.assertEqual(ids(sort_tasks([a, b, c])), [2, 1, 3])


class TestNullPolicy(unittest.TestCase):
    def test_nulls_go_last_in_their_bucket(self):
        no_date = T(1, github_created_at=None)
        very_old = T(2, github_created_at=BASE - timedelta(days=365))
        self.assertEqual(ids(sort_tasks([no_date, very_old])), [2, 1])

    def test_all_null_bucket_falls_back_to_created_at_then_id(self):
        a = T(1, created_at=BASE - timedelta(days=2))
        b = T(2, created_at=BASE)
        c = T(3, created_at=BASE - timedelta(days=1))
        self.assertEqual(ids(sort_tasks([a, b, c])), [2, 3, 1])

    def test_created_at_none_does_not_raise(self):
        self.assertEqual(len(sort_tasks([T(1, created_at=None), T(2)])), 2)


class TestRobustness(unittest.TestCase):
    def test_mixing_aware_and_naive_does_not_raise(self):
        # The regression this design is most exposed to: one tz-aware value would otherwise
        # raise TypeError mid-sort and 500 the whole Tasks page.
        aware = T(1, github_created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc))
        naive = T(2, github_created_at=BASE - timedelta(days=1))
        self.assertEqual(ids(sort_tasks([aware, naive])), [1, 2])

    def test_aware_created_at_also_safe(self):
        aware = T(1, created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(len(sort_tasks([aware, T(2)])), 2)

    def test_output_is_independent_of_input_order(self):
        tasks = [
            T(1, StatusEnum.TODO, BASE - timedelta(days=3), github_issue_number=1),
            T(2, StatusEnum.TESTING, BASE, github_issue_number=2),
            T(3, StatusEnum.TODO, BASE - timedelta(days=1), github_issue_number=3),
            T(4, StatusEnum.DONE, None, github_issue_number=4),
            T(5, StatusEnum.TODO, None, github_issue_number=5),
        ]
        expected = ids(sort_tasks(tasks))
        for rotation in range(len(tasks)):
            rotated = tasks[rotation:] + tasks[:rotation]
            self.assertEqual(ids(sort_tasks(rotated)), expected,
                             f"order changed for rotation {rotation}")

    def test_empty_list(self):
        self.assertEqual(sort_tasks([]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
