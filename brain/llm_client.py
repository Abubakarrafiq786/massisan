import httpx
from core.logger import get_logger
from core.config import get_settings

log = get_logger(__name__)
settings = get_settings()

class LLMClient:
    def __init__(self):
        self.base_url = settings.ollama.base_url
        self.model = settings.ollama.model

    async def generate_response(self, prompt: str, language: str = "en") -> str:
        system_prompt = (
            "You are JARVIS, a helpful conversational assistant. "
            "Answer the user's intent directly and briefly. Do not repeat, quote, "
            "or merely paraphrase the user's message unless asked."
        )
        if language == "ur":
            system_prompt += (
                " The user message comes from speech recognition and may contain "
                "minor grammar errors. Infer the intended meaning and answer it; "
                "do not describe the transcription or copy the user's sentence. "
                "Reply only in natural Urdu script, not Hindi or English. If the "
                "meaning is unclear, ask one brief clarification question in Urdu. "
                "Examples: if the user asks 'کیا حال ہے آپ کے؟', reply "
                "'میں بالکل ٹھیک ہوں، شکریہ! آپ کیسے ہیں؟'. If the user says "
                "'السلام علیکم', reply 'وعلیکم السلام! آپ کی کیا مدد کر سکتا ہوں؟'."
            )

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                return response.json().get("message", {}).get("content", "")
            except Exception as e:
                log.error(f"Ollama API error: {e}")
                return "I'm sorry, I couldn't reach my local brain (Ollama)."