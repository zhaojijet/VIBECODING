import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.nlp.local_qwen import local_llm as llm_client
from app.core.config import settings

app = FastAPI(title="Qwen LLM Standalone Service", version="1.0")


class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: str = "You are a helpful assistant."
    max_tokens: int = settings.LLM_MAX_TOKENS
    temperature: float = settings.LLM_TEMPERATURE


class GenerateResponse(BaseModel):
    response: str


@app.on_event("startup")
async def startup_event():
    # Trigger model loading
    print("Pre-loading model...")
    # Using a dummy prompt to ensure model is loaded into memory
    await llm_client.generate(
        "Verify", "System", settings.LLM_MAX_TOKENS, settings.LLM_TEMPERATURE
    )
    print("Model ready.")


@app.post("/generate", response_model=GenerateResponse)
async def generate_text(req: GenerateRequest):
    try:
        response = await llm_client.generate(
            req.prompt, req.system_prompt, req.max_tokens, req.temperature
        )
        return GenerateResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "model": llm_client.model_path}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=settings.LLM_PORT)
