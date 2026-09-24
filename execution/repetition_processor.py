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
from dashboard_app.app.utils.timezone_utils import (
    convert, display_now, get_display_timezone_name, resolve_timezone)

def process_repetitions(mock_today=None, tz_name=None):
    """Checks repetitive tasks and resets them if the time criteria is met.

    The reset boundary is the local calendar day in DISPLAY_TIMEZONE -- local midnight for
    daily, local Monday for weekly, the local 1st for monthly -- not UTC midnight. With a
    UTC boundary and an operator at UTC-4, a "daily" task rolled over at 20:00 their time.

    🔴 Both sides of the comparison are converted, which is the whole subtlety. `updated_at`
    is stored naive UTC; converting only "today" swaps one off-by-one for another. Worked
    example: a task updated 2026-09-09 02:00Z has UTC date 09-09 but Caracas date 09-08, so
    comparing its *UTC* date against local-today 09-09 would skip a reset that is due.

    `mock_today` (test seam) is interpreted as wall-clock in the configured zone -- it *is*
    the local "today" being injected, not a UTC instant to convert. An aware value is
    honoured as given. `tz_name` overrides the configured zone, so a test can exercise a
    non-UTC zone without mutating process env.
    """
    session = get_session()
    tz = resolve_timezone(tz_name if tz_name is not None else get_display_timezone_name())
    if mock_today is not None:
        local_today = (mock_today.astimezone(tz).date() if mock_today.tzinfo
                       else mock_today.date())
    else:
        local_today = display_now(tz_name).date()
    
    # Fetch all repetitive tasks
    repetitive_tasks = session.query(Task).filter(
        Task.status.in_([StatusEnum.REPEAT_DAILY, StatusEnum.REPEAT_WEEKLY, StatusEnum.REPEAT_MONTHLY])
    ).all()
    
    updated_tasks = []
    
    for task in repetitive_tasks:
        should_reset = False

        # Stored naive UTC -> the configured zone, so both sides of the comparison below
        # live in the same frame of reference. Defensive against a NULL updated_at, which
        # the column allows even though the mixin always populates it.
        updated_local = convert(task.updated_at, tz)
        if updated_local is None:
            continue
        updated_date = updated_local.date()

        # Check based on status
        if task.status == StatusEnum.REPEAT_DAILY:
            # Resets to Todo if updated_at's local date is before the local today
            if updated_date < local_today:
                should_reset = True

        elif task.status == StatusEnum.REPEAT_WEEKLY:
            # Resets to Todo if the local today is Monday and updated_at precedes it
            if local_today.weekday() == 0 and updated_date < local_today:
                should_reset = True

        elif task.status == StatusEnum.REPEAT_MONTHLY:
            # Resets to Todo if the local today is the 1st and updated_at precedes it
            if local_today.day == 1 and updated_date < local_today:
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
