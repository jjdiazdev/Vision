import json
import requests
import os
import importlib
from orchestrator.prompts import SYSTEM_PROMPT
from orchestrator.validator import validate_action
from orchestrator.gateway import LLMGateway

class Orchestrator:
    def __init__(self, model=None, host=None):
        self.system_prompt = SYSTEM_PROMPT
        self.gateway = LLMGateway()
        
        # Load agent actions dynamically
        self.actions_module = importlib.import_module("execution.agent_actions")

    def process_command(self, user_input, backend="local", initial_history=None):
        """
        Sends user input to the selected LLM backend and executes the returned action.
        Supports multi-step chaining within a single user request and multi-turn context.
        """
        # Build initial history string from previous turns if provided
        history_str = ""
        if initial_history:
            for entry in initial_history:
                history_str += f"{entry}\n"
        
        history_str += f"User: \"{user_input}\""
        max_iterations = 30
        final_message = ""
        action_history = []  # Track executed actions to prevent loops
        
        try:
            navigation_target = None
            for i in range(max_iterations):
                print(f"[Orchestrator] Loop Iteration {i+1} (Backend: {backend})...")
                
                # 1. Get response from LLM Gateway
                raw_response = self.gateway.get_response(self.system_prompt, history_str, backend=backend)
                print(f"[Orchestrator] Raw LLM Response: {raw_response}")

                # 2. Parse JSON
                command_data = self._parse_json(raw_response)

                # Auto-correct params if it's a string hallucination
                if isinstance(command_data, dict) and isinstance(command_data.get("params"), str):
                    params_str = command_data["params"].strip()
                    if params_str.startswith("{") and params_str.endswith("}"):
                        try:
                            # Replace single quotes with double quotes for valid JSON
                            command_data["params"] = json.loads(params_str.replace("'", '"'))
                        except Exception:
                            pass
                    elif "=" in params_str:
                        from urllib.parse import parse_qs
                        parsed_qs = parse_qs(params_str)
                        if parsed_qs:
                            command_data["params"] = {k: v[0] for k, v in parsed_qs.items()}

                # If parsing failed, treat the raw response as a chat message and return it directly
                if command_data is None and raw_response.strip():
                    return {
                        "status": "success",
                        "action": "chat_response",
                        "result": raw_response.strip(),
                        "navigation": None
                    }

                # 3. Validate Action and Parameters
                is_valid, error_msg = validate_action(command_data)
                if not is_valid:
                    print(f"[Orchestrator] Validation Error: {error_msg}")
                    # Auto-correct common LLM JSON hallucination (.action, .actio, etc. instead of action)
                    if isinstance(command_data, dict) and "action" not in command_data:
                        for k in list(command_data.keys()):
                            if k.lower() in [".action", ".actio", "actio", "action_name", "tool"]:
                                command_data["action"] = command_data.pop(k)
                                is_valid, error_msg = validate_action(command_data)
                                break
                    
                    # If still invalid, append the validation error to the loop to force LLM self-correction
                    if not is_valid:
                        history_str += f"\nAssistant: {raw_response}\nSystem Note: {error_msg}. Retrying..."
                        continue

                action = command_data.get("action")
                params = command_data.get("params", {})
                message = command_data.get("message", "")

                # Loop Prevention: Don't execute the same mutation twice in a row with same params
                action_signature = f"{action}:{json.dumps(params, sort_keys=True)}"
                if action_signature in action_history:
                    print(f"[Orchestrator] Safeguard Triggered: Duplicate action detected. Stopping loop.")
                    return {
                        "status": "success", 
                        "action": "chat_response", 
                        "result": final_message or f"Action {action} already performed. Stopping to prevent duplication.", 
                        "navigation": navigation_target
                    }
                
                action_history.append(action_signature)

                # 4. Execute Action
                result = self._execute_action(action, params)
                
                # Detect Navigation Intent
                if isinstance(result, str) and result.startswith("NAVIGATE:"):
                    navigation_target = result.split(":", 1)[1]
                    print(f"[Orchestrator] Navigation Target Detected: {navigation_target}")

                # Accumulate feedback messages for the UI
                if message:
                    if final_message:
                        final_message += "\n\n" + message
                    else:
                        final_message = message

                # Append descriptive tool results (except for internal search/conversation)
                if action not in ["search_entities", "chat_response", "navigate_to"] and result and isinstance(result, str):
                    if final_message:
                        if result.strip() != message.strip():
                            final_message += "\n\n" + result
                    else:
                        final_message = result

                # Update history for the next iteration
                history_str += f"\nAssistant: {raw_response}\nTool Result: {result}"

                # 5. Check if we should continue or stop
                # Terminal actions: Conversational and Navigation actions.
                # Listing/Search tools are non-terminal so the LLM can read their results and continue working.
                terminal_actions = [
                    "chat_response",
                    "navigate_to"
                ]
                if action in terminal_actions:
                    # Return the raw tool result directly for terminal actions to avoid mixing with earlier error notes.
                    # Use final_message if available, or fall back to result
                    display_result = final_message if final_message else (result if result else "Action completed.")
                    return {
                        "status": "success",
                        "action": action,
                        "result": display_result,
                        "tool_result": result,
                        "navigation": navigation_target
                    }
                
                # For mutation tools, we continue the loop to allow the LLM to verify success.
                print(f"[Orchestrator] Action '{action}' completed. Continuing iteration...")
                continue

            return {"status": "error", "message": "Maximum autonomous iterations reached.", "navigation": navigation_target}

        except Exception as e:
            print(f"[Orchestrator] Error: {e}")
            return {"status": "error", "message": str(e)}

    def warmup(self):
        """
        Sends an empty request to Ollama to load the model into memory.
        """
        try:
            host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            model = os.environ.get("OLLAMA_MODEL", "phi3.5")
            url = f"{host}/api/generate"
            payload = {
                "model": model,
                "keep_alive": -1
            }
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Orchestrator] Warmup Error: {e}")
            return False

    def _parse_json(self, raw_text):
        """
        Attempts to extract and parse JSON from the raw text.
        Resilient to models that include preamble or reasoning text.
        """
        if not raw_text or not isinstance(raw_text, str):
            print(f"[Orchestrator] Invalid raw_text for parsing: {type(raw_text)}")
            return None
            
        try:
            # 1. Try to find the JSON block using curly braces
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_candidate = raw_text[start_idx:end_idx+1]
                return json.loads(json_candidate)
            
            # 2. Fallback to existing logic if no braces found
            return json.loads(raw_text)
        except Exception as e:
            print(f"[Orchestrator] JSON Parsing Error: {e}")
            return None

    def _execute_action(self, action_name, params):
        """
        Dynamically calls a function from agent_actions.py.
        """
        func = getattr(self.actions_module, action_name, None)
        if not func:
            raise ValueError(f"Action '{action_name}' not found in agent_actions.py")

        print(f"[Orchestrator] Executing {action_name} with params: {params}")
        # Call the function with unpacked parameters
        return func(**params)

if __name__ == "__main__":
    # Quick manual test
    orchestrator = Orchestrator()
    # Mocking a response for validation if Ollama is not available
    print("Orchestrator initialized.")
