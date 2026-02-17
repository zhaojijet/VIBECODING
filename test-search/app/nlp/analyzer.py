import json
from app.nlp.remote_qwen import remote_llm as llm_client


class QueryAnalyzer:
    SYSTEM_PROMPT = """
    You are a Geo-Intent Extractor. Analyze the user's search query and extract structured data.
    Return ONLY a JSON object with these keys:
    - category (str): The type of place (e.g., "cafe", "park", "restaurant"). If unknown, use null.
    - location_hint (str): A specific location mentioned (e.g., "The Bund", "Pudong"). If none, use null.
    - sort_preference (str): "popularity", "distance", or "relevance". Default to "relevance".
    - keywords (list[str]): List of important single-word keywords from the query.
    - key_phrases (list[str]): List of important multi-word phrases.
    - key_info (str): A concise summary of the core user request.
    
    Example:
    Query: "popular coffee near the bund with wifi"
    Output: {
        "category": "cafe",
        "location_hint": "The Bund",
        "sort_preference": "popularity",
        "keywords": ["coffee", "wifi"],
        "key_phrases": ["The Bund", "free wifi"],
        "key_info": "User wants a popular cafe near The Bund with wifi."
    }
    """

    def _extract_json(self, response: str):
        """Extract JSON object from LLM response heavily mixed with text."""
        # 1. Remove <think> blocks
        if "<think>" in response:
            response = response.split("</think>")[-1].strip()

        # 2. Try to find the outer-most JSON object
        start = response.find("{")
        end = response.rfind("}") + 1

        if start != -1 and end != -1:
            json_str = response[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # 3. Fallback: Try cleaning markdown code blocks
        clean_response = response.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_response)
        except json.JSONDecodeError:
            return None

    async def analyze(self, query: str) -> dict:
        try:
            response = await llm_client.generate(query, self.SYSTEM_PROMPT)
            data = self._extract_json(response)

            if not data:
                raise ValueError("Failed to parse JSON")

            # Ensure new fields exist even if LLM misses them
            data.setdefault("keywords", [])
            data.setdefault("key_phrases", [])
            data.setdefault("key_info", "")

            return data
        except Exception:
            # Fallback
            return {
                "category": None,
                "location_hint": None,
                "sort_preference": "relevance",
                "keywords": [],
                "key_phrases": [],
                "key_info": "",
            }


analyzer = QueryAnalyzer()
