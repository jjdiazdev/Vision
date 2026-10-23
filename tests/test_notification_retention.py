"""Notification History retention: the table keeps only the newest NOTIFICATION_HISTORY_LIMIT rows,
pruned on every insert from all three writers (record_notification and both trigger_ui_refresh
copies). Runs against a temporary SQLite file; the SSE notify thread is patched out. Run on its own
process, like the other DB suites:

    python -m unittest tests.test_notification_retention
"""
import os
import sys
import unittest
from unittest import mock

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Force a test database (temporary file) -- before anything opens an engine.
TEST_DB_PATH = os.path.join(BASE_DIR, 'dashboard_app', 'instance', 'test_notification_app.db')
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB_PATH}'

from dashboard_app.app import create_app
from dashboard_app.app.extensions import db
from dashboard_app.app.main.routes import record_notification
from dashboard_app.app.models import NOTIFICATION_HISTORY_LIMIT, Notification, prune_notifications
from execution import agent_actions, log_progress


class TestNotificationRetention(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        cls.app_context.pop()
        agent_actions.get_session().get_bind().dispose()
        for path in (TEST_DB_PATH, TEST_DB_PATH + "-wal", TEST_DB_PATH + "-shm"):
            if os.path.exists(path):
                os.remove(path)

    def setUp(self):
        Notification.query.delete()
        db.session.commit()

    def _seed(self, n):
        db.session.add_all(Notification(message=f"n{i}") for i in range(n))
        db.session.commit()

    def _ids(self):
        return [i for (i,) in db.session.query(Notification.id).order_by(Notification.id)]

    def test_limit_is_500(self):
        self.assertEqual(NOTIFICATION_HISTORY_LIMIT, 500)

    def test_prune_boundaries(self):
        for n, expected_deleted in ((0, 0), (499, 0), (500, 0), (501, 1)):
            with self.subTest(n=n):
                self.setUp()
                self._seed(n)
                self.assertEqual(prune_notifications(db.session), expected_deleted)
                db.session.commit()
                self.assertEqual(Notification.query.count(), min(n, 500))

    def test_prune_keeps_newest_ids(self):
        self._seed(10)
        ids = self._ids()
        self.assertEqual(prune_notifications(db.session, keep=3), 7)
        db.session.commit()
        self.assertEqual(self._ids(), ids[-3:])

    def test_record_notification_caps_history(self):
        self._seed(500)
        oldest = self._ids()[0]
        record_notification("newest", "success")
        db.session.commit()
        self.assertEqual(Notification.query.count(), 500)
        self.assertNotIn(oldest, self._ids())
        self.assertEqual(Notification.query.order_by(Notification.id.desc()).first().message, "newest")

    def test_trigger_ui_refresh_caps_history(self):
        for module in (agent_actions, log_progress):
            with self.subTest(module=module.__name__):
                self.setUp()
                self._seed(500)
                oldest = self._ids()[0]
                with mock.patch.object(module.threading, "Thread"):
                    module.trigger_ui_refresh("x", toast={"message": "newest", "type": "info"})
                db.session.expire_all()
                self.assertEqual(Notification.query.count(), 500)
                self.assertNotIn(oldest, self._ids())
                self.assertEqual(Notification.query.order_by(Notification.id.desc()).first().message, "newest")


if __name__ == '__main__':
    unittest.main()
