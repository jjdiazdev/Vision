import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path so we can import orchestrator
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.gateway import LLMGateway

def test_nvidia_connection():
    # Load .env file
    load_dotenv()
    
    print("--- V.I.S.I.O.N. LLM Gateway Diagnostic ---")
    
    api_key = os.environ.get("NVIDIA_API_KEY")
    model = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-4-340b-instruct")
    
    if not api_key or api_key == "your_nvidia_api_key_here":
        print("[!] ERROR: NVIDIA_API_KEY is not set in .env")
        return

    print(f"[*] Testing Cloud Backend: {model}")
    print(f"[*] API Key Found: {api_key[:5]}...{api_key[-5:]}")
    
    gateway = LLMGateway()
    
    system_prompt = "You are a diagnostic tool. Respond with valid JSON only."
    history = "User: Respond with {'status': 'connected'} if you can hear me."
    
    try:
        print("[*] Sending request to NVIDIA NIM...")
        # Force cloud backend for testing
        response = gateway.get_response(system_prompt, history, backend="cloud")
        
        print("\n[+] CLOUD RESPONSE RECEIVED:")
        print("-" * 30)
        print(response)
        print("-" * 30)
        
        if "connected" in response.lower():
            print("\n[SUCCESS] NVIDIA NIM is fully operational.")
        else:
            print("\n[WARNING] Response received, but it might not be in the expected format.")
            
    except Exception as e:
        print(f"\n[FAILURE] Cloud request failed: {e}")
        print("[*] Falling back to check if Local Ollama would have caught this...")
        try:
            local_response = gateway._get_ollama_response(system_prompt, history)
            print("[+] LOCAL FALLBACK VERIFIED (Ollama responded).")
        except Exception as local_e:
            print(f"[!] LOCAL ERROR: Even Ollama is unreachable: {local_e}")

if __name__ == "__main__":
    test_nvidia_connection()
