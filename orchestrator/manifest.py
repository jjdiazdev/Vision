# Tool Specification for the LLM Orchestrator

TOOL_MANIFEST = [
    {
        "name": "create_system",
        "description": "Creates a new system (a GitHub organization) with a name and an optional GitHub org login.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The human-readable name of the system."
                },
                "github_org": {
                    "type": "string",
                    "description": "Optional GitHub organization login this system corresponds to."
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "update_system",
        "description": "Updates an existing system's name or GitHub org login. REQUIRES numeric system_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "system_id": {
                    "type": "integer",
                    "description": "The unique ID of the system to update."
                },
                "name": {
                    "type": "string",
                    "description": "The new name for the system."
                },
                "github_org": {
                    "type": "string",
                    "description": "The new GitHub organization login for the system."
                }
            },
            "required": ["system_id"]
        }
    },
    {
        "name": "delete_system",
        "description": "Deletes a system from the system (also deletes its projects and their tasks). REQUIRES numeric system_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "system_id": {
                    "type": "integer",
                    "description": "The unique ID of the system to delete."
                }
            },
            "required": ["system_id"]
        }
    },
    {
        "name": "list_systems",
        "description": "Retrieves a list of all current systems.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "create_project",
        "description": "Creates a new project (a GitHub repo) with a name and an optional initial status. Optionally belongs to a system.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The human-readable name of the project."
                },
                "status": {
                    "type": "string",
                    "enum": ["Todo", "In-Progress", "Testing", "Done", "Blocked"],
                    "description": "The initial status of the project. Defaults to 'Todo'."
                },
                "system_id": {
                    "type": "integer",
                    "description": "Optional ID of the system this project belongs to."
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "update_project",
        "description": "Updates an existing project's name, status, or parent system. REQUIRES numeric project_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The unique ID of the project to update."
                },
                "name": {
                    "type": "string",
                    "description": "The new name for the project."
                },
                "status": {
                    "type": "string",
                    "enum": ["Todo", "In-Progress", "Testing", "Done", "Blocked"],
                    "description": "The new status for the project."
                },
                "system_id": {
                    "type": "integer",
                    "description": "The ID of the system this project should belong to."
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "delete_project",
        "description": "Deletes a project from the system (also deletes its tasks). REQUIRES numeric project_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The unique ID of the project to delete."
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "list_projects",
        "description": "Retrieves a list of all current projects, optionally filtered by system_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "system_id": {
                    "type": "integer",
                    "description": "Optional ID of the system to filter projects by."
                }
            },
            "required": []
        }
    },
    {
        "name": "create_task",
        "description": "Creates a new task within a specific project. REQUIRES numeric project_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the task."
                },
                "project_id": {
                    "type": "integer",
                    "description": "The ID of the project this task belongs to."
                },
                "employee_id": {
                    "type": "integer",
                    "description": "Optional ID of the employee assigned to the task."
                },
                "status": {
                    "type": "string",
                    "enum": ["Todo", "In-Progress", "Testing", "Done", "Blocked"],
                    "description": "The initial status of the task. Defaults to 'Todo'."
                }
            },
            "required": ["name", "project_id"]
        }
    },
    {
        "name": "update_task",
        "description": "Updates an existing task's status, name, assigned employee, or parent project. REQUIRES numeric task_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "The unique ID of the task to update."
                },
                "status": {
                    "type": "string",
                    "enum": ["Todo", "In-Progress", "Testing", "Done", "Blocked"],
                    "description": "The new status for the task."
                },
                "name": {
                    "type": "string",
                    "description": "The new name for the task."
                },
                "employee_id": {
                    "type": "integer",
                    "description": "The ID of the employee to assign to this task. Use 0 to unassign."
                },
                "project_id": {
                    "type": "integer",
                    "description": "The ID of the project to move this task to."
                }
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "delete_task",
        "description": "Deletes a task from the system. REQUIRES numeric task_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "The unique ID of the task to delete."
                }
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "list_tasks",
        "description": "Retrieves a list of tasks, optionally filtered by project_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Optional ID of the project to filter tasks by."
                }
            },
            "required": []
        }
    },
    {
        "name": "create_employee",
        "description": "Adds a new employee to the system.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The full name of the employee."
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "update_employee",
        "description": "Updates an existing employee's details. REQUIRES numeric employee_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "integer",
                    "description": "The unique ID of the employee to update."
                },
                "name": {
                    "type": "string",
                    "description": "The new full name for the employee."
                }
            },
            "required": ["employee_id"]
        }
    },
    {
        "name": "delete_employee",
        "description": "Deletes an employee from the system. REQUIRES numeric employee_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "integer",
                    "description": "The unique ID of the employee to delete."
                }
            },
            "required": ["employee_id"]
        }
    },
    {
        "name": "list_employees",
        "description": "Retrieves a list of all employees in the system.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_entities",
        "description": "Searches for numeric IDs of employees, systems, projects, or tasks by their name. Use this to find IDs for other tool calls.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["employee", "system", "project", "task"],
                    "description": "The type of entity to search for."
                },
                "query": {
                    "type": "string",
                    "description": "The name or part of the name to search for."
                }
            },
            "required": ["entity_type", "query"]
        }
    },
    {
        "name": "chat_response",
        "description": "Used for general conversation or greetings when no other tool is appropriate.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "navigate_to",
        "description": "Programmatically navigates the Dashboard UI to a different view. Can navigate to general sections or specific system/project details.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "The target view. Use 'index', 'employees', 'systems', 'projects', or 'tasks'. For a specific system detail, use 'system:ID' (e.g., 'system:2'). For a specific project detail, use 'project:ID' (e.g., 'project:5')."
                }
            },
            "required": ["destination"]
        }
    }
]
