import os
import sys

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from execution.agent_actions import create_project, create_process, create_task

def populate():
    print("Starting database population...")
    
    # Project 1: High Tech Initiative (Long Name)
    p1_id = create_project("Quantum Synthetic Intelligence Platform & Neural Network Decentralization").split(": ")[1]
    
    # Project 2: Simple Short Name
    p2_id = create_project("Mars").split(": ")[1]
    
    # Project 3: Mixed Name
    p3_id = create_project("Operation Deep Sea Exploratory Mission Phase 4", status="In-Progress").split(": ")[1]

    # Processes for P1
    proc1_id = create_process("Architecture & Multi-Layer Schema Definition for Neural Synapse Mapping", int(p1_id)).split(": ")[1].split(" ")[0]
    proc2_id = create_process("Backend Core Development", int(p1_id)).split(": ")[1].split(" ")[0]
    
    # Processes for P2
    proc3_id = create_process("Landing Site Analysis", int(p2_id)).split(": ")[1].split(" ")[0]
    
    # Tasks for Proc 1 (Long Task Names)
    create_task("Draft comprehensive architectural diagram for the distributed ledger system including consensus protocols", int(proc1_id), employee_id=2, status="In-Progress")
    create_task("Security Audit of the encrypted communication layer between edge nodes and central hub", int(proc1_id), employee_id=3, status="Todo")
    
    # Tasks for Proc 2
    create_task("API Implementation", int(proc2_id), employee_id=4, status="Testing")
    create_task("Database Optimization for high-concurrency write operations in WAL mode", int(proc2_id), employee_id=5, status="Done")
    
    # Tasks for Proc 3
    create_task("Analyze soil composition", int(proc3_id), employee_id=2, status="Blocked")
    create_task("Deploy weather monitoring satellites into low orbit for atmospheric pressure monitoring", int(proc3_id), employee_id=3, status="Todo")

    print("Population complete.")

if __name__ == "__main__":
    populate()
