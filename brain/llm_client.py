import httpx
from core.logger import get_logger
from core.config import get_settings

log = get_logger(__name__)
settings = get_settings()

class LLMClient:
    def __init__(self):
        self.base_url = settings.ollama.base_url
        self.model = settings.ollama.model

    async def generate_response(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                return response.json().get("response", "")
            except Exception as e:
                log.error(f"Ollama API error: {e}")
                return "I'm sorry, I couldn't reach my local brain (Ollama)."