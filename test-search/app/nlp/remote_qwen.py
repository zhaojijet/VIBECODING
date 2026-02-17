import aiohttp
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class RemoteQwenAgent:
    def __init__(self):
        self.api_url = settings.LLM_API_URL

    async def generate(
        self, prompt: str, system_prompt: str = "You are a helpful assistant."
    ) -> str:
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "temperature": settings.LLM_TEMPERATURE,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "")
                    else:
                        error_text = await resp.text()
                        logger.error(f"LLM Service Error: {resp.status} - {error_text}")
                        return "FAILED"
        except Exception as e:
            logger.error(f"Failed to connect to LLM Service: {e}")
            return "ERROR"


remote_llm = RemoteQwenAgent()
