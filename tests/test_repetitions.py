import unittest
from datetime import datetime, timedelta
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Force a test database (temporary file)
TEST_DB_PATH = os.path.join(BASE_DIR, 'dashboard_app', 'instance', 'test_app.db')
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except:
        pass

os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB_PATH}'

from dashboard_app.app import create_app
from dashboard_app.app.models import Task, StatusEnum, Project
from dashboard_app.app.extensions import db
from execution.repetition_processor import process_repetitions

class TestRepetitions(unittest.TestCase):
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
        # Dispose of engine while context is still active
        db.engine.dispose()
        cls.app_context.pop()
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except:
                pass

    def setUp(self):
        # Clear data before each test
        db.session.query(Task).delete()
        db.session.query(Project).delete()
        db.session.commit()

        # Create a test project
        project = Project(name="Test Project")
        db.session.add(project)
        db.session.commit()

        self.project_id = project.id

    def test_daily_repetition(self):
        # Create a daily task updated yesterday
        today = datetime(2026, 6, 15) # Monday
        yesterday = today - timedelta(days=1)
        
        task = Task(name="Daily", status=StatusEnum.REPEAT_DAILY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        
        task.updated_at = yesterday
        db.session.commit()
        
        count = process_repetitions(mock_today=today)
        self.assertEqual(count, 1)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.TODO)

    def test_weekly_repetition_on_monday(self):
        # Create a weekly task updated last week
        monday = datetime(2026, 6, 15) # A Monday
        last_friday = monday - timedelta(days=3)
        
        task = Task(name="Weekly", status=StatusEnum.REPEAT_WEEKLY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        
        task.updated_at = last_friday
        db.session.commit()
        
        # Run on Monday -> Should reset
        count = process_repetitions(mock_today=monday)
        self.assertEqual(count, 1)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.TODO)

    def test_weekly_repetition_on_tuesday(self):
        # Create a weekly task updated last week
        tuesday = datetime(2026, 6, 16) # A Tuesday
        last_friday = tuesday - timedelta(days=4)
        
        task = Task(name="Weekly", status=StatusEnum.REPEAT_WEEKLY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        
        task.updated_at = last_friday
        db.session.commit()
        
        # Run on Tuesday -> Should NOT reset
        count = process_repetitions(mock_today=tuesday)
        self.assertEqual(count, 0)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.REPEAT_WEEKLY)

    def test_monthly_repetition_on_1st(self):
        # Create a monthly task updated last month
        first_of_month = datetime(2026, 7, 1)
        last_month = datetime(2026, 6, 20)
        
        task = Task(name="Monthly", status=StatusEnum.REPEAT_MONTHLY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        
        task.updated_at = last_month
        db.session.commit()
        
        # Run on 1st -> Should reset
        count = process_repetitions(mock_today=first_of_month)
        self.assertEqual(count, 1)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.TODO)

    def test_monthly_repetition_on_2nd(self):
        # Create a monthly task updated last month
        second_of_month = datetime(2026, 7, 2)
        last_month = datetime(2026, 6, 20)
        
        task = Task(name="Monthly", status=StatusEnum.REPEAT_MONTHLY, project_id=self.project_id)
        db.session.add(task)
        db.session.commit()
        
        task.updated_at = last_month
        db.session.commit()
        
        # Run on 2nd -> Should NOT reset
        count = process_repetitions(mock_today=second_of_month)
        self.assertEqual(count, 0)
        db.session.refresh(task)
        self.assertEqual(task.status, StatusEnum.REPEAT_MONTHLY)

if __name__ == '__main__':
    unittest.main()
