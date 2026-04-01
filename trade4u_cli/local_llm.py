import requests
import json

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"

class LocalLLM:
    def __init__(self, model=None, url=None):
        self.model = model or DEFAULT_MODEL
        self.url = url or DEFAULT_OLLAMA_URL
        self.available = self._check_connection()
    
    def _check_connection(self):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def is_available(self):
        return self.available
    
    def chat(self, prompt, system_prompt=None):
        if not self.available:
            return None
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(self.url, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get("response", "")
        except:
            pass
        return None
    
    def list_models(self):
        if not self.available:
            return []
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except:
            pass
        return []

llm = LocalLLM()

SYSTEM_PROMPT = """You are Trade4U, a friendly AI trading assistant. You help users with:
- Stock prices and market data
- Portfolio tracking and analysis
- Market news and trends
- Crypto prices
- Investment recommendations

Keep responses short and conversational. Use emojis where appropriate. 
If you don't know something, say so honestly.
"""

def ask_ai(query, context=""):
    full_prompt = f"Context: {context}\n\nUser: {query}\n\nAssistant:"
    return llm.chat(full_prompt, SYSTEM_PROMPT)

def is_ai_available():
    return llm.is_available()
