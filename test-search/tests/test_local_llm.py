import asyncio
import pytest
from mlx_lm import load, generate


@pytest.mark.asyncio
async def test_model():
    model_path = "data/models/Qwen3-0.6B-MLX-bf16"
    print(f"Loading model: {model_path}...")

    try:
        model, tokenizer = load(model_path)

        prompt = "Where is Shanghai?"
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        print("Generating...")
        response = generate(model, tokenizer, prompt=text, verbose=True, max_tokens=100)
        print("\nResponse:", response)

    except Exception as e:
        print(f"Error loading model: {e}")


if __name__ == "__main__":
    asyncio.run(test_model())
