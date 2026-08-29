import os
import time
from pathlib import Path

TRIGGER_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))) / '.tmp' / 'triggers'

def trigger_task_update(task_id):
    """Create a trigger file for an agent to notice an update."""
    if not TRIGGER_DIR.exists():
        TRIGGER_DIR.mkdir(parents=True, exist_ok=True)
    trigger_file = TRIGGER_DIR / f'task_{task_id}.trigger'
    with open(trigger_file, 'w') as f:
        f.write(f'Updated at: {time.ctime()}')

def trigger_project_update(project_id):
    """Create a trigger file for an agent to notice an update."""
    if not TRIGGER_DIR.exists():
        TRIGGER_DIR.mkdir(parents=True, exist_ok=True)
    trigger_file = TRIGGER_DIR / f'project_{project_id}.trigger'
    with open(trigger_file, 'w') as f:
        f.write(f'Updated at: {time.ctime()}')
