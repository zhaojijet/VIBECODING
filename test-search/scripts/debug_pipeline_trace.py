import asyncio
import json
import os
import sys

# Add the project root directory to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.nlp.analyzer import analyzer
from app.nlp.rewriter import rewriter
from app.recall.es_client import es_client
from app.core.config import settings


# Setup logging to file and console
class Tee(object):
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()


LOG_FILE = settings.TRACE_LOG_PATH
os.makedirs(settings.LOG_DIR, exist_ok=True)
f = open(LOG_FILE, "a")
sys.stdout = Tee(sys.stdout, f)


async def trace_query(query: str, lat: float, lon: float):
    # radius from settings
    radius_km = settings.DEFAULT_RADIUS_KM
    print(f"\n{'='*60}", flush=True)
    print(f"QUERY: {query}", flush=True)
    print(f"{'='*60}", flush=True)

    # 1. NLP Phase
    print("\n--- [Phase 1] NLP Module ---", flush=True)
    # Sequential execution to avoid blocking the single-threaded LLM server
    print("Running Analyzer...", flush=True)
    intent = await analyzer.analyze(query)
    print("Running Rewriter...", flush=True)
    rewrites = await rewriter.rewrite(query)

    print(
        f"Intent Analysis:\n{json.dumps(intent, indent=2, ensure_ascii=False)}",
        flush=True,
    )
    print(
        f"Rewrites:\n{json.dumps(rewrites, indent=2, ensure_ascii=False)}", flush=True
    )

    # 2. Recall Phase
    print("\n--- [Phase 2] Recall Module (Parallel Queues) ---", flush=True)
    # Using generic center of Shanghai if no specific lat/lon provided for the user,
    # but for this test we simulate a user at People's Square (31.2304, 121.4737)
    radius_km = 10.0

    # A. Analysis Sub-Queues
    print(f"\n[Sub-Queue A] Analysis Sub-Queues:", flush=True)

    # A. Analysis Sub-Queues
    print(f"\n[Sub-Queue A] Analysis Sub-Queues:", flush=True)

    # A1. Key Phrases (Aggregated)
    if intent.get("key_phrases"):
        print(
            f"  > [A-1] Key Phrases (Aggregated): {intent['key_phrases']}", flush=True
        )
        results_ph = await es_client._search_sub_queue(
            intent["key_phrases"],
            "phrases_agg",
            intent,
            lat,
            lon,
            radius_km,
            "analysis_phrases",
        )
        for j, c in enumerate(results_ph[:3]):
            print(
                f"    [{j+1}] ID: {c['id']} | {c['name']} (Score: {c['es_score']:.2f}, Dist: {c.get('distance_km', 'N/A'):.2f}km)",
                flush=True,
            )

    # A2. Keywords (Aggregated)
    if intent.get("keywords"):
        print(f"  > [A-2] Keywords (Aggregated): {intent['keywords']}", flush=True)
        results_kw = await es_client._search_sub_queue(
            intent["keywords"],
            "keywords_agg",
            intent,
            lat,
            lon,
            radius_km,
            "analysis_keywords",
        )
        for j, c in enumerate(results_kw[:3]):
            print(
                f"    [{j+1}] ID: {c['id']} | {c['name']} (Score: {c['es_score']:.2f}, Dist: {c.get('distance_km', 'N/A'):.2f}km)",
                flush=True,
            )

    # A3. Key Info
    if intent.get("key_info"):
        print(f"  > [A-3] Key Info: {intent['key_info']}", flush=True)
        results_info = await es_client._search_sub_queue(
            intent["key_info"],
            "key_info",
            intent,
            lat,
            lon,
            radius_km,
            "analysis_info",
        )
        for j, c in enumerate(results_info[:3]):
            print(
                f"    [{j+1}] ID: {c['id']} | {c['name']} (Score: {c['es_score']:.2f}, Dist: {c.get('distance_km', 'N/A'):.2f}km)",
                flush=True,
            )

    # B. Rewriting Queues
    print(f"\n[Sub-Queue B] Rewriting Queues:", flush=True)
    for i, exp in enumerate(rewrites):
        print(f"  > [B] Rewrite [{i+1}]: {exp}", flush=True)
        results_rw = await es_client._search_sub_queue(
            exp, "rewrite", intent, lat, lon, radius_km, "rewriting"
        )
        for j, c in enumerate(results_rw[:3]):
            print(
                f"    [{j+1}] ID: {c['id']} | {c['name']} (Score: {c['es_score']:.2f}, Dist: {c.get('distance_km', 'N/A'):.2f}km)",
                flush=True,
            )

    # Merged Results (Simulating es_client.search logic or calling it)
    print(f"\n[Merged & Deduplicated] Final Candidates:", flush=True)
    candidates = await es_client.search(
        original_query=query,
        expansions=rewrites,
        nlp_analysis=intent,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
    )

    print(f"Total Candidates: {len(candidates)}", flush=True)
    for i, c in enumerate(candidates[:10]):  # Show top 10 candidates raw
        print(
            f"[{i+1}] ID: {c['id']} | {c['name']} (Score: {c['es_score']:.2f}, Dist: {c.get('distance_km', 'N/A'):.2f}km, Source: {c.get('recall_source')})",
            flush=True,
        )

    # 3. Ranking Phase
    print("\n--- [Phase 3] Ranking Module (Top 10) ---", flush=True)
    ranked_results = ranker.rank(
        candidates,
        user_lat=lat,
        user_lon=lon,
        sort_preference=intent.get("sort_preference", "relevance"),
    )

    for i, r in enumerate(ranked_results):
        print(f"#{i+1} ID: {r['id']} | {r['name']}", flush=True)
        print(f"    Source: {r.get('recall_source')}", flush=True)
        print(f"    Category: {r.get('category')}", flush=True)
        print(f"    Location: {r.get('location')}", flush=True)
        print(
            f"    Score: {r['final_score']:.4f} (ES: {r['es_score']:.2f}, Pop: {r['popularity']})",
            flush=True,
        )


async def main():
    # User at People's Square
    user_lat = 31.2304
    user_lon = 121.4737

    # Test Case 1
    await trace_query("田子坊", user_lat, user_lon)

    # Test Case 2
    await trace_query("上海公园", user_lat, user_lon)


if __name__ == "__main__":
    asyncio.run(main())
