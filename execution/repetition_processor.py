import os
import sys
from datetime import datetime, timedelta

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from execution.db_client import get_session
from dashboard_app.app.models import Task, StatusEnum
from dashboard_app.app.utils.trigger import trigger_task_update
from dashboard_app.app.utils.sse import announcer

def process_repetitions(mock_today=None):
    """Checks repetitive tasks and resets them if the time criteria is met."""
    session = get_session()
    today = mock_today or datetime.utcnow()
    
    # Fetch all repetitive tasks
    repetitive_tasks = session.query(Task).filter(
        Task.status.in_([StatusEnum.REPEAT_DAILY, StatusEnum.REPEAT_WEEKLY, StatusEnum.REPEAT_MONTHLY])
    ).all()
    
    updated_tasks = []
    
    for task in repetitive_tasks:
        should_reset = False
        
        # Check based on status
        if task.status == StatusEnum.REPEAT_DAILY:
            # Resets to Todo if updated_at date < today
            if task.updated_at.date() < today.date():
                should_reset = True
                
        elif task.status == StatusEnum.REPEAT_WEEKLY:
            # Resets to Todo if today is Monday and updated_at date < today
            if today.weekday() == 0 and task.updated_at.date() < today.date():
                should_reset = True
                
        elif task.status == StatusEnum.REPEAT_MONTHLY:
            # Resets to Todo if today is the 1st and updated_at date < today
            if today.day == 1 and task.updated_at.date() < today.date():
                should_reset = True
                
        if should_reset:
            task.status = StatusEnum.TODO
            updated_tasks.append(task.id)
            print(f"Resetting task {task.id} ('{task.name}') to Todo.")
    
    if updated_tasks:
        session.commit()
        # Trigger UI refresh for each task
        for task_id in updated_tasks:
            trigger_task_update(task_id)
        
        # Notify SSE
        announcer.announce("update_tasks")
    
    session.close()
    return len(updated_tasks)

if __name__ == "__main__":
    count = process_repetitions()
    print(f"Processed {count} repetitive tasks.")
