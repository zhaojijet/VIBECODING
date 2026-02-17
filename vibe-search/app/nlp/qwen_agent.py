from app.core.config import settings

import aiohttp
import logging
import os

logger = logging.getLogger(__name__)


class QwenAgent:
    def __init__(self):
        # Default to the standalone service port
        self.api_url = os.getenv("LLM_SERVICE_URL", "http://localhost:8001/generate")

    async def generate(
        self, prompt: str, system_prompt: str = "You are a helpful assistant."
    ) -> str:
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": 200,
            "temperature": 0.7,
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
                        return ""
        except Exception as e:
            logger.error(f"Failed to connect to LLM Service: {e}")
            return ""


llm_client = QwenAgent()
