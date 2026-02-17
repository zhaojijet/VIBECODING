import asyncio
from elasticsearch import AsyncElasticsearch
from geopy.distance import geodesic
from app.core.config import settings


class ESClient:
    def __init__(self):
        self.client = AsyncElasticsearch(settings.ES_HOST)
        self.index = settings.ES_INDEX

    async def search(
        self,
        original_query: str,
        expansions: list[str],
        nlp_analysis: dict,
        lat: float,
        lon: float,
        radius_km: float = None,
    ):
        if radius_km is None:
            radius_km = settings.DEFAULT_RADIUS_KM
        # Parallel Execution of Sub-Queues
        # 1. Prepare parallel tasks
        tasks = []

        # A. Analysis Sub-Queues
        # A1. Key Phrases (Aggregated)
        if nlp_analysis.get("key_phrases"):
            tasks.append(
                self._search_sub_queue(
                    query_content=nlp_analysis["key_phrases"],
                    query_type="phrases_agg",
                    nlp_analysis=nlp_analysis,
                    lat=lat,
                    lon=lon,
                    radius_km=radius_km,
                    source_tag="analysis_phrases",
                )
            )

        # A2. Keywords (Aggregated)
        if nlp_analysis.get("keywords"):
            tasks.append(
                self._search_sub_queue(
                    query_content=nlp_analysis["keywords"],
                    query_type="keywords_agg",
                    nlp_analysis=nlp_analysis,
                    lat=lat,
                    lon=lon,
                    radius_km=radius_km,
                    source_tag="analysis_keywords",
                )
            )

        # A3. Key Info (Semantic Summary)
        if nlp_analysis.get("key_info"):
            tasks.append(
                self._search_sub_queue(
                    query_content=nlp_analysis["key_info"],
                    query_type="key_info",
                    nlp_analysis=nlp_analysis,
                    lat=lat,
                    lon=lon,
                    radius_km=radius_km,
                    source_tag="analysis_info",
                )
            )

        # B. Rewriting Queues (N tasks)
        for exp in expansions:
            tasks.append(
                self._search_sub_queue(
                    query_content=exp,
                    query_type="rewrite",
                    nlp_analysis=nlp_analysis,
                    lat=lat,
                    lon=lon,
                    radius_km=radius_km,
                    source_tag="rewriting",
                )
            )

        # Execute all sub-queues
        all_results_lists = await asyncio.gather(*tasks)

        # Merge & Dedup
        seen_ids = set()
        merged_candidates = []
        mapped_candidates = {}

        # Flatten results
        for sub_queue_results in all_results_lists:
            for candidate in sub_queue_results:
                cid = candidate["id"]
                if cid not in mapped_candidates:
                    mapped_candidates[cid] = candidate
                    merged_candidates.append(candidate)  # Preserve order
                    seen_ids.add(cid)
                else:
                    # Append source if already exists
                    prev_source = mapped_candidates[cid].get("recall_source", "")
                    curr_source = candidate.get("recall_source", "")

                    # Merge sources
                    if curr_source not in prev_source:
                        mapped_candidates[cid][
                            "recall_source"
                        ] = f"{prev_source}, {curr_source}"

        return merged_candidates

    async def _search_sub_queue(
        self, query_content, query_type, nlp_analysis, lat, lon, radius_km, source_tag
    ):
        """
        Generic Sub-Queue Handler
        query_type: 'phrases_agg', 'keywords_agg', 'key_info', 'rewrite'
        query_content: string or list of strings
        """
        must_clauses = [
            {
                "geo_distance": {
                    "distance": f"{radius_km}km",
                    "location": {"lat": lat, "lon": lon},
                }
            }
        ]

        should_clauses = []
        min_should_match = 1

        # logic based on type
        if query_type == "phrases_agg":
            # Target `key_phrases` field specifically
            for phrase in query_content:
                should_clauses.append(
                    {
                        "match_phrase": {
                            "key_phrases": {
                                "query": phrase,
                                "boost": settings.BOOST_PHRASE,
                            }
                        }
                    }
                )
            min_should_match = 2 if len(should_clauses) > 1 else 1

        elif query_type == "keywords_agg":
            # Target `keywords` field specifically
            for kw in query_content:
                should_clauses.append(
                    {
                        "match": {
                            "keywords": {"query": kw, "boost": settings.BOOST_KEYWORD}
                        }
                    }
                )
            min_should_match = 2 if len(should_clauses) > 1 else 1

        elif query_type == "key_info":
            # Target `key_info` field specifically
            should_clauses.append(
                {
                    "match": {
                        "key_info": {
                            "query": query_content,
                            "boost": settings.BOOST_INFO,
                        }
                    }
                }
            )
            min_should_match = 1  # Single clause, keep at 1

        elif query_type == "rewrite":
            # Loose Match on multiple text fields including AI rewrites
            should_clauses.append(
                {
                    "match": {
                        "name": {"query": query_content, "boost": settings.BOOST_NAME}
                    }
                }
            )
            should_clauses.append(
                {
                    "match": {
                        "address": {
                            "query": query_content,
                            "boost": settings.BOOST_ADDR,
                        }
                    }
                }
            )
            should_clauses.append(
                {
                    "match": {
                        "rewrites": {
                            "query": query_content,
                            "boost": settings.BOOST_REWRITE,
                        }
                    }
                }
            )
            should_clauses.append(
                {"match": {"amenity": {"query": query_content, "boost": 1.0}}}
            )
            should_clauses.append(
                {"match": {"tags": {"query": query_content, "boost": 1.0}}}
            )
            min_should_match = 2

        elif query_type == "original":
            # Original Query on name, address and rewrites
            should_clauses.append(
                {
                    "match": {
                        "name": {"query": query_content, "boost": settings.BOOST_NAME}
                    }
                }
            )
            should_clauses.append(
                {
                    "match": {
                        "address": {
                            "query": query_content,
                            "boost": settings.BOOST_ADDR,
                        }
                    }
                }
            )
            should_clauses.append(
                {
                    "match": {
                        "rewrites": {
                            "query": query_content,
                            "boost": settings.BOOST_REWRITE,
                        }
                    }
                }
            )
            min_should_match = 2

        # Global Category Boost (Apply to all)
        if nlp_analysis.get("category"):
            cat = nlp_analysis["category"]
            should_clauses.append(
                {"match": {"amenity": {"query": cat, "boost": settings.BOOST_CATEGORY}}}
            )
            if query_type == "keyword" or query_type == "original":
                # For broad queries, category match helps
                pass

        query = {
            "bool": {
                "must": must_clauses,
                "should": should_clauses,
                "minimum_should_match": min_should_match,
            }
        }

        results = await self._execute_query(
            query, size=settings.SEARCH_SIZE, lat=lat, lon=lon
        )
        for r in results:
            r["recall_source"] = source_tag
        return results

    async def _execute_query(self, query, size, lat, lon):
        try:
            # Debug: Check for index existence before searching?
            # No, just let it fail or succeed.
            # Note: The index name used is self.index (poi_v1).
            resp = await self.client.search(index=self.index, query=query, size=size)

            results = []
            seen_ids = set()
            seen_content = set()

            for hit in resp["hits"]["hits"]:
                parsed = self._parse_hit(hit, lat, lon)

                # 1. ID Dedup
                if parsed["id"] in seen_ids:
                    continue
                seen_ids.add(parsed["id"])

                # 2. Content Dedup (Handle dirty data with unique IDs but same content)
                # Use name + approx location (100m precision)
                name = parsed.get("name")
                loc = parsed.get("location")

                if name and loc:
                    p_lat = loc["lat"]
                    p_lon = loc["lon"]
                    # Round based on dedup precision (default 3 decimals ~100m)
                    precision = settings.DEDUP_PRECISION
                    content_key = (
                        name,
                        round(p_lat, precision),
                        round(p_lon, precision),
                    )

                    if content_key in seen_content:
                        continue
                    seen_content.add(content_key)

                results.append(parsed)
            return results
        except Exception as e:
            print(f"ES Search Context Error: {e}")
            return []

    def _parse_hit(self, hit, lat, lon):
        source = hit["_source"]

        dist_km = None
        if source.get("location") and lat is not None and lon is not None:
            try:
                item_lat = source["location"]["lat"]
                item_lon = source["location"]["lon"]
                dist_km = geodesic((lat, lon), (item_lat, item_lon)).km
            except Exception:
                pass

        return {
            "id": hit["_id"],
            "name": source.get("name"),
            "location": source.get("location"),
            "category": source.get("category"),
            "popularity": source.get("popularity", 0),
            "es_score": hit["_score"],
            "distance_km": dist_km,
        }


es_client = ESClient()
