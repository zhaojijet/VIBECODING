import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.recall.es_client import ESClient


@pytest.mark.asyncio
async def test_parallel_recall_search():
    # Mock AsyncElasticsearch
    with patch("app.recall.es_client.AsyncElasticsearch") as MockES:
        mock_es_instance = AsyncMock()
        MockES.return_value = mock_es_instance

        # Mock search response
        # First call (Analysis): Returns [A, B]
        # Second call (Rewriting): Returns [B, C]
        mock_es_instance.search.side_effect = [
            {
                "hits": {
                    "hits": [
                        {"_id": "1", "_score": 1, "_source": {"name": "A"}},
                        {"_id": "2", "_score": 1, "_source": {"name": "B"}},
                    ]
                }
            },
            {
                "hits": {
                    "hits": [
                        {"_id": "2", "_score": 1, "_source": {"name": "B"}},
                        {"_id": "3", "_score": 1, "_source": {"name": "C"}},
                    ]
                }
            },
        ]

        client = ESClient()

        # input data
        original_query = "coffee"
        expansions = ["exp1"]
        nlp_analysis = {"keywords": ["coffee"], "category": "cafe"}

        results = await client.search(
            original_query, expansions, nlp_analysis, 31.23, 121.47
        )

        # Verify Parallel Calls
        assert mock_es_instance.search.call_count == 2

        # Verify Dedup (A, B, B, C -> A, B, C)
        assert len(results) == 3
        ids = sorted([r["id"] for r in results])
        assert ids == ["1", "2", "3"]

        print("\n[PASS] Parallel recall executed and merged correctly.")
