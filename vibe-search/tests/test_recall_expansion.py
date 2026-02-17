import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.recall.es_client import ESClient


@pytest.mark.asyncio
async def test_search_query_construction():
    # Mock AsyncElasticsearch
    with patch("app.recall.es_client.AsyncElasticsearch") as MockES:
        mock_es_instance = AsyncMock()
        MockES.return_value = mock_es_instance

        # Mock search response
        mock_es_instance.search.return_value = {"hits": {"hits": []}}

        client = ESClient()

        # input data
        original_query = "popular coffee near bund"
        expansions = ["exp1", "exp2", "exp3"]
        nlp_analysis = {
            "key_phrases": ["The Bund", "free wifi"],
            "keywords": ["coffee", "wifi"],
            "category": "cafe",
            "sort_preference": "popularity",
        }

        await client.search(original_query, expansions, nlp_analysis, 31.23, 121.47)

        # Verify the call args
        call_args = mock_es_instance.search.call_args
        assert call_args is not None

        query_body = call_args.kwargs["query"]
        bool_query = query_body["bool"]

        # Check Must (Geo)
        assert bool_query["must"][0]["geo_distance"]["distance"] == "5.0km"

        # Check Should (Strategies)
        should_clauses = bool_query["should"]

        # 1. Precision Queue (Phrases = Boost 4.0)
        phrases = [
            c
            for c in should_clauses
            if "match_phrase" in c and c["match_phrase"]["name"]["boost"] == 4.0
        ]
        assert len(phrases) == 2
        assert phrases[0]["match_phrase"]["name"]["query"] == "The Bund"

        # 2. Precision Queue (Keywords = Boost 3.0)
        keywords_name = [
            c
            for c in should_clauses
            if "match" in c and c["match"].get("name", {}).get("boost") == 3.0
        ]
        keywords_amenity = [
            c
            for c in should_clauses
            if "term" in c and c["term"].get("amenity", {}).get("boost") == 3.0
        ]
        assert len(keywords_name) == 2
        assert len(keywords_amenity) == 2

        # 3. Base Queue (Original = Boost 2.0 / 1.5)
        base_name = [
            c
            for c in should_clauses
            if "match" in c and c["match"].get("name", {}).get("boost") == 2.0
        ]
        base_tags = [
            c
            for c in should_clauses
            if "match" in c and c["match"].get("tags", {}).get("boost") == 1.5
        ]
        assert len(base_name) == 1
        assert len(base_tags) == 1
        assert base_name[0]["match"]["name"]["query"] == original_query

        # 4. Expansion Queue (Rewrites = Boost 1.0)
        exp_clauses = [
            c
            for c in should_clauses
            if "match" in c and c["match"].get("name", {}).get("boost") == 1.0
        ]
        assert len(exp_clauses) == 3
        assert exp_clauses[0]["match"]["name"]["query"] == "exp1"

        # Check Filter (Category)
        filters = bool_query["filter"]
        assert filters[0]["term"]["amenity"] == "cafe"

        print("\n[PASS] ES Query constructed with correct Multi-Strategy Logic.")
