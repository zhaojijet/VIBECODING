import json
from app.nlp.remote_qwen import remote_llm as llm_client


class QueryRewriter:
    SYSTEM_PROMPT = """
    You are a Search Query Expander. Generate exactly 3 semantically similar or related queries for the user's input to improve search recall.
    Return ONLY a JSON list of 3 strings.
    
    Example:
    Query: "cheap coffee"
    Output: ["affordable cafe", "budget coffee shop", "low cost espresso"]
    """

    def _extract_json_list(self, response: str):
        """Extract JSON list from LLM response heavily mixed with text."""
        # 1. Remove <think> blocks
        if "<think>" in response:
            response = response.split("</think>")[-1].strip()

        # 2. Try to find the outer-most JSON list
        start = response.find("[")
        end = response.rfind("]") + 1

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

    async def rewrite(self, query: str) -> list[str]:
        try:
            response = await llm_client.generate(query, self.SYSTEM_PROMPT)
            params = self._extract_json_list(response)

            if isinstance(params, list):
                return params
            return []
        except Exception:
            return []


rewriter = QueryRewriter()
