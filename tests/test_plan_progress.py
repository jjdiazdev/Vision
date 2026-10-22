"""Plan feature end to end against a temporary SQLite file: import -> sync (GitHub stubbed) ->
plan-scoped progress, Tasks filter and the graph API. No network: fetch_issues_by_number and
trigger_ui_refresh are patched. Run on its own process, like the other DB suites:

    python -m unittest tests.test_plan_progress
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Force a test database (temporary file) -- before anything opens an engine.
TEST_DB_PATH = os.path.join(BASE_DIR, 'dashboard_app', 'instance', 'test_plan_app.db')
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB_PATH}'
os.environ['DISPLAY_TIMEZONE'] = 'UTC'

from dashboard_app.app import create_app
from dashboard_app.app.extensions import db
from dashboard_app.app.models import Plan, PlanItem, PlanStatusEnum, Project, StatusEnum, System, Task
from execution import agent_actions, plan_sync

SPEC = {
    "name": "Week 43", "org": "acme-org", "target_date": "2026-10-29",
    "groups": [{"key": "API", "label": "Backend", "repo": "acme-org/api"}],
    "nodes": [
        {"key": "main", "group": "API", "kind": "base", "label": "origin/main"},
        {"key": "B1", "group": "API", "issue": 1, "display_key": "B-01", "label": "Contract"},
        {"key": "B2", "group": "API", "issue": 2, "label": "Schedules"},
        {"key": "B3", "group": "API", "issue": 3, "label": "Templates"},
    ],
    "edges": [
        {"from": "main", "to": "B1", "kind": "base"},
        {"from": "B1", "to": "B2", "kind": "stacked"},
        {"from": "B2", "to": "B3", "kind": "stacked"},
    ],
}


def _gh_issue(number, state="OPEN", pr=None):
    closing = []
    if pr:
        pr_number, pr_state = pr
        closing.append({"number": pr_number, "state": pr_state, "merged": pr_state == "MERGED",
                        "isDraft": False, "reviewDecision": None,
                        "repository": {"nameWithOwner": "acme-org/api"},
                        "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": "SUCCESS"}}}]}})
    return {"number": number, "title": f"Issue {number}", "state": state,
            "stateReason": "COMPLETED" if state == "CLOSED" else None,
            "closedByPullRequestsReferences": {"nodes": closing}, "timelineItems": {"nodes": []}}


class TestPlanFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()
        cls.refresh_patch = mock.patch.object(agent_actions, "trigger_ui_refresh")
        cls.refresh_mock = cls.refresh_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.refresh_patch.stop()
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        cls.app_context.pop()
        agent_actions.get_session().get_bind().dispose()
        for path in (TEST_DB_PATH, TEST_DB_PATH + "-wal", TEST_DB_PATH + "-shm"):
            if os.path.exists(path):
                os.remove(path)

    def setUp(self):
        for model in (PlanItem, Plan, Task, Project, System):
            model.query.delete()
        db.session.commit()
        system = System(name="acme-org", github_org="acme-org")
        db.session.add(system)
        db.session.flush()
        self.project = Project(name="api", github_repo="acme-org/api", system_id=system.id, status=StatusEnum.TODO)
        db.session.add(self.project)
        db.session.flush()
        # 2 plan issues mirrored as Tasks (both Done) + 8 old backlog Tasks still Todo.
        for number in (1, 2):
            db.session.add(Task(name=f"Issue {number}", project_id=self.project.id, status=StatusEnum.DONE,
                                github_issue_number=number))
        for number in range(100, 108):
            db.session.add(Task(name=f"Old {number}", project_id=self.project.id, status=StatusEnum.TODO,
                                github_issue_number=number))
        db.session.commit()
        self.refresh_mock.reset_mock()

    def _import(self, spec=SPEC):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(spec, fh)
        try:
            return agent_actions.import_plan(fh.name)
        finally:
            os.remove(fh.name)

    def _sync(self, issues):
        session = agent_actions.get_session()
        try:
            with mock.patch.object(plan_sync, "fetch_issues_by_number",
                                   side_effect=lambda owner, repo, numbers, fields: {n: issues.get(n) for n in numbers}):
                return plan_sync.sync_plan_once(session)
        finally:
            session.close()
            db.session.expire_all()

    def _client(self):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['authenticated'] = True
        return client

    def test_import_links_tasks_and_activates(self):
        msg = self._import()
        self.assertIn("3 issues", msg)
        self.assertIn("2 linked", msg)
        plan = Plan.query.one()
        self.assertTrue(plan.is_active)
        self.assertEqual([i.key for i in plan.items], ["main", "B1", "B2", "B3"])

    def test_import_rejects_unlinked_repo(self):
        spec = dict(SPEC, groups=[{"key": "API", "label": "Backend", "repo": "acme-org/missing"}])
        self.assertIn("no Project is linked to acme-org/missing", self._import(spec))
        self.assertEqual(Plan.query.count(), 0)

    def test_new_import_deactivates_previous_plan(self):
        self._import()
        self._import(dict(SPEC, name="Week 44"))
        active = Plan.query.filter_by(is_active=True).all()
        self.assertEqual([p.name for p in active], ["Week 44"])

    def test_sync_sets_status_and_toasts_only_transitions(self):
        self._import()
        summary = self._sync({1: _gh_issue(1, "CLOSED", (10, "MERGED")), 2: _gh_issue(2, pr=(11, "MERGED")), 3: _gh_issue(3)})
        self.assertEqual(summary["transitions"], 0)  # first sync: no toast
        statuses = {i.key: i.plan_status for i in PlanItem.query.filter_by(node_kind="issue")}
        self.assertEqual(statuses, {"B1": PlanStatusEnum.CLOSED, "B2": PlanStatusEnum.MERGED, "B3": PlanStatusEnum.NO_PR})

        self.refresh_mock.reset_mock()
        summary = self._sync({1: _gh_issue(1, "CLOSED", (10, "MERGED")), 2: _gh_issue(2, pr=(11, "MERGED")), 3: _gh_issue(3, pr=(12, "OPEN"))})
        self.assertEqual(summary["transitions"], 1)
        toast = self.refresh_mock.call_args.kwargs["toast"]
        self.assertEqual(toast["message"], "B3 #3: PR #12 open")

        self.refresh_mock.reset_mock()
        self.assertEqual(self._sync({1: _gh_issue(1, "CLOSED", (10, "MERGED")), 2: _gh_issue(2, pr=(11, "MERGED")),
                                     3: _gh_issue(3, pr=(12, "OPEN"))})["updated"], 0)
        self.refresh_mock.assert_not_called()

    def test_progress_is_scoped_to_plan_issues(self):
        client = self._client()
        # Without a plan: legacy ratio, 2 Done of 10 Tasks.
        self.assertIn(b"20%", client.get("/projects").data)
        self._import()
        self._sync({1: _gh_issue(1, "CLOSED", (10, "MERGED")), 2: _gh_issue(2, pr=(11, "MERGED")), 3: _gh_issue(3)})
        page = client.get("/projects").data
        self.assertIn(b"67%", page)          # 2 of 3 plan issues merged or closed
        self.assertIn(b"2/3 in plan", page)

    def test_tasks_list_is_filtered_to_plan(self):
        client = self._client()
        self._import()
        page = client.get("/tasks").data.decode()
        self.assertIn("Issue 1", page)
        self.assertNotIn("Old 100", page)
        page = client.get("/tasks?f_plan=all").data.decode()
        self.assertIn("Old 100", page)
        partial = client.get("/api/updates/tasks?f_plan=all").data.decode()
        self.assertIn("Old 100", partial)

    def test_tasks_list_unfiltered_without_plan(self):
        page = self._client().get("/tasks").data.decode()
        self.assertIn("Old 100", page)
        self.assertNotIn("Plan only", page)

    def test_graph_api(self):
        client = self._client()
        self.assertIsNone(client.get("/api/plans/graph").get_json()["plan"])
        self._import()
        self._sync({1: _gh_issue(1, "CLOSED", (10, "MERGED")), 2: _gh_issue(2, pr=(11, "MERGED")), 3: _gh_issue(3)})
        data = client.get("/api/plans/graph").get_json()
        self.assertEqual(data["plan"]["progress"], {"done": 2, "total": 3, "percent": 67})
        group = data["plan"]["groups"][0]
        self.assertEqual(group["total"], 3)
        self.assertTrue(group["mermaid"].startswith("graph LR"))
        self.assertIn("n1 --> n2", group["mermaid"])   # B1 closed: B2 no longer stacked
        self.assertIn("n2 --> n3", group["mermaid"])   # B2 merged: B3 no longer stacked
        self.assertEqual(data["cross_edges"], [])
        b3 = next(n for n in data["nodes"] if n["key"] == "B3")
        self.assertEqual((b3["status"], b3["mid"], b3["task_id"]), ("sinpr", "n3", None))

    def test_graph_page_renders_and_api_is_gated(self):
        self.assertEqual(self.app.test_client().get("/api/plans/graph").status_code, 401)
        page = self._client().get("/tasks?view=graph").data.decode()
        self.assertIn('x-data="planGraph(', page)
        self.assertIn('aria-current="page"', page)


if __name__ == '__main__':
    unittest.main()
