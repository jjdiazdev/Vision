from orchestrator.manifest import TOOL_MANIFEST

def validate_action(command_data):
    """
    Validates the action name and parameters against the TOOL_MANIFEST.
    Includes type checking to prevent hallucinations.
    """
    if not isinstance(command_data, dict):
        return False, "Command data must be a dictionary."

    action_name = command_data.get("action")
    params = command_data.get("params", {})

    if not isinstance(params, dict):
        return False, f"Parameter 'params' must be a dictionary, got {type(params).__name__}."

    if not action_name:
        return False, "Missing 'action' key in command data."

    # Find the tool in the manifest
    tool = next((t for t in TOOL_MANIFEST if t["name"] == action_name), None)
    if not tool:
        return False, f"Action '{action_name}' is not a recognized tool."

    # Validate required parameters
    tool_params = tool.get("parameters", {})
    properties = tool_params.get("properties", {})
    required_params = tool_params.get("required", [])
    
    for req in required_params:
        if req not in params:
            return False, f"Missing required parameter '{req}' for action '{action_name}'."

    # Validate parameter names and TYPES
    for param_name, param_value in params.items():
        if param_name not in properties:
            return False, f"Unexpected parameter '{param_name}' for action '{action_name}'."
        
        # Simple type checking to prevent placeholder string hallucinations
        expected_type = properties[param_name].get("type")
        
        if expected_type == "integer":
            if not isinstance(param_value, int) and not (isinstance(param_value, str) and param_value.isdigit()):
                return False, f"Parameter '{param_name}' must be an integer, got '{param_value}'."
        elif expected_type == "string":
            if not isinstance(param_value, str):
                return False, f"Parameter '{param_name}' must be a string."

    return True, None
