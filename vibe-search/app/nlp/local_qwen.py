import os
from mlx_lm import load, generate


from app.core.config import settings


class LocalQwenAgent:
    def __init__(self):
        self.model_path = settings.LLM_MODEL_PATH
        self.model = None
        self.tokenizer = None

    def _ensure_model(self):
        if self.model is None:
            print(f"Loading local model: {self.model_path}...")
            self.model, self.tokenizer = load(self.model_path)
            print("Model loaded.")

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        self._ensure_model()

        # Apply chat template
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        # MLX generation
        response = generate(
            self.model,
            self.tokenizer,
            prompt=text,
            max_tokens=max_tokens,
            temp=temperature,
            verbose=False,
        )
        return response


local_llm = LocalQwenAgent()
