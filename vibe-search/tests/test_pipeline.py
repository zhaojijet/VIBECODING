import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app
from app.models import SearchRequest
from httpx import AsyncClient, ASGITransport

# Mock Responses
MOCK_INTENT = {
    "category": "cafe",
    "location_hint": "The Bund",
    "sort_preference": "distance",
}
MOCK_REWRITES = ["coffee shop", "starbucks", "espresso"]
MOCK_ES_HITS = [
    {
        "id": "1",
        "name": "Starbucks Reserve",
        "location": {"lat": 31.2304, "lon": 121.4737},  # Near Bund
        "category": "cafe",
        "popularity": 95,
        "es_score": 10.0,
    },
    {
        "id": "2",
        "name": "Far Away Cafe",
        "location": {"lat": 31.1000, "lon": 121.4000},  # Far
        "category": "cafe",
        "popularity": 20,
        "es_score": 5.0,
    },
]


@pytest.mark.asyncio
async def test_search_pipeline():
    # Patch the high-level methods directly to avoid singleton collisions
    with patch(
        "app.nlp.analyzer.QueryAnalyzer.analyze", new_callable=AsyncMock
    ) as mock_analyze:
        mock_analyze.return_value = MOCK_INTENT

        with patch(
            "app.nlp.rewriter.QueryRewriter.rewrite", new_callable=AsyncMock
        ) as mock_rewrite:
            mock_rewrite.return_value = MOCK_REWRITES

            # Mock ES Return
            with patch(
                "app.recall.es_client.AsyncElasticsearch.search", new_callable=AsyncMock
            ) as mock_es:
                mock_es.return_value = {
                    "hits": {
                        "hits": [
                            {"_id": "1", "_source": MOCK_ES_HITS[0], "_score": 10.0},
                            {"_id": "2", "_source": MOCK_ES_HITS[1], "_score": 5.0},
                        ]
                    }
                }

                # Test API
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as ac:
                    response = await ac.post(
                        "/search",
                        json={
                            "query": "coffee near bund",
                            "lat": 31.2300,
                            "lon": 121.4700,
                        },
                    )

                assert response.status_code == 200
                data = response.json()

                # Verify NLP
                assert data["intent"]["category"] == "cafe"
                assert "coffee shop" in data["rewrites"]

                # Verify Ranking
                results = data["results"]
                assert len(results) == 2
                assert results[0]["name"] == "Starbucks Reserve"
