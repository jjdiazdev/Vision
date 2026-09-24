import unittest
from datetime import datetime, timedelta
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Force a test database (temporary file)
TEST_DB_PATH = os.path.join(BASE_DIR, 'dashboard_app', 'instance', 'test_edge_cases.db')
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except:
        pass

os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB_PATH}'
# Pin the reset boundary to UTC. process_repetitions() now derives the local calendar day from
# DISPLAY_TIMEZONE, so without this the assertions below would depend on the ambient container
# env -- and the midnight `updated_at` values in these suites are exactly what flips under a
# negative-offset zone.
os.environ['DISPLAY_TIMEZONE'] = 'UTC'

from dashboard_app.app import create_app
from dashboard_app.app.models import Task, StatusEnum, Project
from dashboard_app.app.extensions import db
from execution.repetition_processor import process_repetitions

class TestRepetitionsEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
        cls.app = create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        cls.app_context.pop()
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except:
                pass

    def setUp(self):
        db.session.query(Task).delete()
        db.session.query(Project).delete()
        db.session.commit()

        project = Project(name="Edge Case Project")
        db.session.add(project)
        db.session.commit()
        self.project_id = project.id

    def test_daily_reset_across_months(self):
        """Test daily reset from last day of month to 1st."""
        june_30 = datetime(2026, 6, 30)
        july_1 = datetime(2026, 7, 1)
        
        task = Task(name="Daily Month End", status=StatusEnum.REPEAT_DAILY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        task.updated_at = june_30
        db.session.commit()
        
        count = process_repetitions(mock_today=july_1)
        self.assertEqual(count, 1)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.TODO)

    def test_weekly_reset_monday_alignment(self):
        """Test weekly reset exactly on Monday after a long gap."""
        last_update = datetime(2026, 6, 1) # Monday
        three_weeks_later = datetime(2026, 6, 22) # Also Monday
        
        task = Task(name="Weekly Gap", status=StatusEnum.REPEAT_WEEKLY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        task.updated_at = last_update
        db.session.commit()
        
        count = process_repetitions(mock_today=three_weeks_later)
        self.assertEqual(count, 1)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.TODO)

    def test_monthly_reset_leap_year(self):
        """Test monthly reset across Feb 29 on a leap year."""
        feb_28 = datetime(2024, 2, 28) # Leap year Feb
        march_1 = datetime(2024, 3, 1)
        
        task = Task(name="Monthly Leap", status=StatusEnum.REPEAT_MONTHLY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        task.updated_at = feb_28
        db.session.commit()
        
        count = process_repetitions(mock_today=march_1)
        self.assertEqual(count, 1)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.TODO)

    def test_monthly_reset_standard_year(self):
        """Test monthly reset across Feb 28 on a standard year."""
        feb_28 = datetime(2026, 2, 28)
        march_1 = datetime(2026, 3, 1)
        
        task = Task(name="Monthly Standard", status=StatusEnum.REPEAT_MONTHLY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        task.updated_at = feb_28
        db.session.commit()
        
        count = process_repetitions(mock_today=march_1)
        self.assertEqual(count, 1)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.TODO)

    def test_no_double_reset_same_day(self):
        """Test that a task already reset today doesn't count again."""
        today = datetime(2026, 6, 1) # 1st of month, also Monday
        
        task = Task(name="No Double", status=StatusEnum.TODO, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        
        # User sets it back to repeat today
        task.status = StatusEnum.REPEAT_DAILY
        task.updated_at = today
        db.session.commit()
        
        count = process_repetitions(mock_today=today)
        self.assertEqual(count, 0)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.REPEAT_DAILY)

    def test_year_end_transition(self):
        """Test reset across New Year's Eve."""
        dec_31 = datetime(2025, 12, 31)
        jan_1 = datetime(2026, 1, 1)
        
        task = Task(name="New Year", status=StatusEnum.REPEAT_MONTHLY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        task.updated_at = dec_31
        db.session.commit()
        
        count = process_repetitions(mock_today=jan_1)
        self.assertEqual(count, 1)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.TODO)

if __name__ == '__main__':
    unittest.main()
