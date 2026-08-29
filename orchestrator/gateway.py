import os
import requests
import json
from openai import OpenAI

class LLMGateway:
    def __init__(self):
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "phi3.5")
        self.nvidia_api_key = os.environ.get("NVIDIA_API_KEY")
        self.nvidia_model = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-4-340b-instruct")
        
        # Initialize OpenAI client for NVIDIA NIM if key is present
        if self.nvidia_api_key:
            self.client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=self.nvidia_api_key
            )
        else:
            self.client = None

    def get_response(self, system_prompt, history, backend="local"):
        """
        Routes the request to the appropriate backend with automatic fallback.
        """
        if backend == "cloud" and self.client:
            try:
                print(f"[LLMGateway] Routing to NVIDIA NIM ({self.nvidia_model})...")
                response = self._get_nvidia_response(system_prompt, history)
                
                if not response or not response.strip():
                    raise ValueError("Empty response from NVIDIA NIM")
                
                return response
            except Exception as e:
                print(f"[LLMGateway] Cloud Error: {e}. Falling back to Local Ollama.")
                # Fallback to local on any cloud failure
                return self._get_ollama_response(system_prompt, history)
        else:
            if backend == "cloud" and not self.client:
                print("[LLMGateway] NVIDIA_API_KEY not configured. Defaulting to Local.")
            
            print(f"[LLMGateway] Routing to Local Ollama ({self.ollama_model})...")
            return self._get_ollama_response(system_prompt, history)

    def _get_nvidia_response(self, system_prompt, history):
        """
        Calls NVIDIA NIM via OpenAI-compatible API.
        """
        response = self.client.chat.completions.create(
            model=self.nvidia_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": history}
            ],
            temperature=0.2,
            max_tokens=1024,
            stream=False,
            # Some NIM models might support json_object mode
            response_format={"type": "json_object"},
            timeout=30.0 # 30s timeout for cloud
        )
        return response.choices[0].message.content

    def _get_ollama_response(self, system_prompt, history):
        """
        Calls local Ollama API.
        """
        url = f"{self.ollama_host}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": f"{system_prompt}\n\n{history}\nOutput:",
            "stream": False,
            "format": "json",
            "keep_alive": -1
        }
        
        try:
            # 30s timeout for local as requested
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.exceptions.Timeout:
            raise RuntimeError("Ollama service timed out (30s limit reached).")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to Ollama. Ensure the service is running.")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama API Error: {str(e)}")
