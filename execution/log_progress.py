import os
import sys
import argparse

# Add the project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from execution.db_client import get_session
from dashboard_app.app.models import Task, StatusEnum, Notification
import requests
import threading

def trigger_ui_refresh(message="update", toast=None, employee_id=None, task_id=None, project_id=None):
    """Notify the Flask app that a change happened to trigger SSE updates."""
    if toast:
        try:
            s = get_session()
            s.add(Notification(message=toast["message"], type=toast.get("type", "info"),
                                employee_id=employee_id, task_id=task_id, project_id=project_id))
            s.commit()
            s.close()
        except Exception as e:
            print(f"Error recording notification: {e}")

    def _notify():
        urls = [
            "http://127.0.0.1:5000/internal/notify-update",
            "http://127.0.0.1:5001/internal/notify-update",
            "http://web:5000/internal/notify-update"
        ]
        payload = {"message": message}
        if toast:
            payload["toast"] = toast
        for url in urls:
            try:
                requests.post(url, json=payload, timeout=0.1)
            except:
                pass
    
    # Run in a separate thread
    threading.Thread(target=_notify, daemon=True).start()

def log_task_progress(task_id, status):
    """
    Simple utility for agents to report task progress.
    """
    session = get_session()
    try:
        task = session.query(Task).get(task_id)
        if not task:
            print(f"Error: Task {task_id} not found.")
            return False
        
        task.status = StatusEnum(status)
        session.commit()
        print(f"Success: Task {task_id} status updated to {status}.")
        trigger_ui_refresh(f"task_progress_{status}", toast={"message": f"Task '{task.name}' updated", "type": "success"}, employee_id=task.employee_id, task_id=task.id, project_id=task.project_id)
        return True
    except Exception as e:
        session.rollback()
        print(f"Error: Failed to update task {task_id}: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Progress Logger")
    parser.add_argument("task_id", type=int, help="The ID of the task being updated")
    parser.add_argument("status", choices=["Todo", "In-Progress", "Testing", "Done", "Blocked", "Repeat Daily", "Repeat Weekly", "Repeat Monthly"], help="The new status")
    
    args = parser.parse_args()
    log_task_progress(args.task_id, args.status)
