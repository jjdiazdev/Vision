import unittest
import os
from unittest.mock import patch, MagicMock
from orchestrator.brain import Orchestrator

class TestIntents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We don't want to actually execute the DB actions during intent testing
        cls.patcher = patch('orchestrator.brain.importlib.import_module')
        cls.mock_import = cls.patcher.start()
        cls.mock_actions = MagicMock()
        cls.mock_import.return_value = cls.mock_actions
        
        # Initialize orchestrator with mocked actions
        cls.orchestrator = Orchestrator()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def test_intent_accuracy(self):
        """
        Suite of natural language sentences and their expected tool calls.
        Note: This tests the FIRST tool call the LLM makes for a given intent.
        """
        test_cases = [
            # Projects
            {
                "input": "Create a project named Project Alpha",
                "expected_action": "create_project",
                "expected_params": {"name": "Project Alpha"}
            },
            {
                "input": "Start a new project called Mars Mission with status In-Progress",
                "expected_action": "create_project",
                "expected_params": {"name": "Mars Mission", "status": "In-Progress"}
            },
            {
                "input": "Show me all projects",
                "expected_action": "list_projects",
                "expected_params": {}
            },
            
            # Employees
            {
                "input": "Add a new employee named John Smith",
                "expected_action": "create_employee",
                "expected_params": {"name": "John Smith"}
            },
            {
                "input": "Register a team member called Alice Johnson",
                "expected_action": "create_employee",
                "expected_params": {"name": "Alice Johnson"}
            },

            # Navigation
            {
                "input": "Take me to the projects page",
                "expected_action": "navigate_to",
                "expected_params": {"destination": "projects"}
            },
            {
                "input": "Go to the dashboard",
                "expected_action": "navigate_to",
                "expected_params": {"destination": "home"}
            },
            {
                "input": "Show the employees table",
                "expected_action": "navigate_to",
                "expected_params": {"destination": "employees"}
            },
            {
                "input": "Open the tasks view",
                "expected_action": "navigate_to",
                "expected_params": {"destination": "tasks"}
            },

            # Search & IDs (Testing if it correctly identifies the need to search or uses provided IDs)
            {
                "input": "Search for a project named Apollo",
                "expected_action": "search_entities",
                "expected_params": {"entity_type": "project", "query": "Apollo"}
            },
            {
                "input": "Find the employee ID for Bob",
                "expected_action": "search_entities",
                "expected_params": {"entity_type": "employee", "query": "Bob"}
            },
            
            # Systems
            {
                "input": "Create a system named Acme",
                "expected_action": "create_system",
                "expected_params": {"name": "Acme"}
            },

            # Tasks
            {
                "input": "Create a task called Fix Login Bug in project 10",
                "expected_action": "create_task",
                "expected_params": {"name": "Fix Login Bug", "project_id": 10}
            },
            {
                "input": "Add a task 'Write Unit Tests' to project 3 and assign it to employee 1",
                "expected_action": "create_task",
                "expected_params": {"name": "Write Unit Tests", "project_id": 3, "employee_id": 1}
            },
            {
                "input": "Update task 123 to Done",
                "expected_action": "update_task",
                "expected_params": {"task_id": 123, "status": "Done"}
            },
            {
                "input": "Rename task 45 to 'Final Review'",
                "expected_action": "update_task",
                "expected_params": {"task_id": 45, "name": "Final Review"}
            },
            {
                "input": "Assign task 88 to employee 7",
                "expected_action": "update_task",
                "expected_params": {"task_id": 88, "employee_id": 7}
            },

            # Deletion
            {
                "input": "Delete project 1",
                "expected_action": "delete_project",
                "expected_params": {"project_id": 1}
            },
            {
                "input": "Remove task 999",
                "expected_action": "delete_task",
                "expected_params": {"task_id": 999}
            },

            # Conversational
            {
                "input": "Hello VISION, how are you today?",
                "expected_action": "chat_response",
                "expected_params": {}
            }
        ]

        results = []
        passed = 0
        total = len(test_cases)

        print("\n" + "="*50)
        print(f"RUNNING INTENT ACCURACY TEST ({total} cases)")
        print("="*50)

        # To avoid making real LLM calls if needed, we could mock the gateway.
        # But Phase 6.1 instructions imply running them THROUGH the orchestrator,
        # which means testing the LLM's reasoning. 
        # I will assume the environment has access to Ollama or the Cloud API.
        
        # We need to capture the LLM's first decision. 
        # Since process_command runs in a loop, we'll patch 'gateway.get_response' 
        # if we wanted to mock the LLM, but here we want to TEST the LLM.
        
        # However, running 20 LLM calls might be slow and requires a backend.
        # I will check if the user wants me to run this against a real backend or mock it.
        # Given "Ensure the LLM correctly maps user requests", I MUST run it against a backend.
        
        # Get backend from environment, default to local if not set
        backend = os.environ.get("TEST_BACKEND", "local")
        print(f"Using backend: {backend}")

        for case in test_cases:
            user_input = case["input"]
            print(f"\n[Test] Input: '{user_input}'")
            
            # We use patch to spy on the actions executed
            with patch.object(self.orchestrator, '_execute_action', wraps=self.orchestrator._execute_action) as spy_execute:
                # Execute command
                response = self.orchestrator.process_command(user_input, backend=backend)
                
                # Get the FIRST action that was actually executed
                # spy_execute.call_args_list is a list of calls
                if spy_execute.call_args_list:
                    # call_args is (args, kwargs)
                    # _execute_action(action_name, params)
                    actual_action = spy_execute.call_args_list[0][0][0]
                    actual_params = spy_execute.call_args_list[0][0][1]
                else:
                    actual_action = response.get("action")
                    actual_params = {}

                # Check if it matched
                action_match = (actual_action == case["expected_action"])
                
                # Verify against the case
                if action_match:
                    print(f"  [OK] Action matched: {actual_action}")
                    passed += 1
                else:
                    print(f"  [FAIL] Expected '{case['expected_action']}', got '{actual_action}'")
                    print(f"  [Response] {response}")

        print("\n" + "="*50)
        print(f"RESULTS: {passed}/{total} ({passed/total*100:.1f}%)")
        print("="*50)
        
        self.assertGreaterEqual(passed/total, 0.8, "Intent accuracy below 80%")

if __name__ == "__main__":
    unittest.main()
