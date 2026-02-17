import asyncio
from fastapi import FastAPI, HTTPException
from app.models import SearchRequest, SearchResponse, POIResult
from app.nlp.analyzer import analyzer
from app.nlp.rewriter import rewriter
from app.recall.es_client import es_client
from app.ranking.ranker import ranker
from app.core.config import settings

app = FastAPI(title="LBS Search Service", version="1.0")


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    # 1. NLP Phase (Parallel)
    # Run Intent Analysis and Query Rewriting concurrently
    intent_task = asyncio.create_task(analyzer.analyze(req.query))
    rewrite_task = asyncio.create_task(rewriter.rewrite(req.query))

    intent, rewrites = await asyncio.gather(intent_task, rewrite_task)

    # 2. Recall Phase
    # Use extracted intent filters and rewritten queries to fetch candidates
    candidates = await es_client.search(
        original_query=req.query,
        expansions=rewrites,
        nlp_analysis=intent,
        lat=req.lat,
        lon=req.lon,
        radius_km=req.radius_km,
    )

    if not candidates:
        return {"intent": intent, "rewrites": rewrites, "results": []}

    # 3. Ranking Phase
    # Sort candidates based on user preference (from intent)
    ranked_candidates = ranker.rank(
        candidates,
        user_lat=req.lat,
        user_lon=req.lon,
        sort_preference=intent.get("sort_preference", "relevance"),
    )

    # Format Response
    results = [
        POIResult(
            id=c["id"],
            name=c["name"],
            category=c["category"],
            distance_km=c["distance_km"],
            popularity=c["popularity"],
            score=c["final_score"],
        )
        for c in ranked_candidates
    ]

    return {"intent": intent, "rewrites": rewrites, "results": results}


@app.get("/health")
async def health():
    return {"status": "ok", "elasticsearch": settings.ES_HOST}
