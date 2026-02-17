import asyncio
import os
import sys
import random
import json
import logging
import osmium
from elasticsearch import Elasticsearch, helpers
from app.nlp.remote_qwen import remote_llm
from app.core.config import settings

# Configuration from centralized settings
ES_HOST = settings.ES_HOST
INDEX_NAME = settings.ES_INDEX
OSM_FILE = settings.OSM_DATA_PATH
BATCH_SIZE = settings.INGEST_BATCH_SIZE
LIMIT = settings.INGEST_LIMIT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class POIHandler(osmium.SimpleHandler):
    def __init__(self):
        super(POIHandler, self).__init__()
        self.buffer = []
        self.count = 0
        self.es = Elasticsearch(ES_HOST)
        self.create_index()

    def create_index(self):
        if not self.es.indices.exists(index=INDEX_NAME):
            mappings = {
                "properties": {
                    "name": {"type": "text", "analyzer": "standard"},
                    "location": {"type": "geo_point"},
                    "category": {"type": "keyword"},
                    "amenity": {"type": "keyword"},
                    "tags": {"type": "object", "enabled": False},
                    "popularity": {"type": "integer"},
                    # New Semantic Fields (AI Generated)
                    "address": {"type": "text", "analyzer": "standard"},
                    "keywords": {"type": "text", "analyzer": "standard"},
                    "key_phrases": {"type": "text", "analyzer": "standard"},
                    "key_info": {"type": "text", "analyzer": "standard"},
                    "rewrites": {"type": "text", "analyzer": "standard"},
                }
            }
            self.es.indices.create(index=INDEX_NAME, mappings=mappings)
            logger.info(f"Created index {INDEX_NAME}")

    def node(self, n):
        if self.count >= LIMIT:
            return
        self.process_feature(n, "node")

    def process_feature(self, feature, feature_type):
        if self.count >= LIMIT:
            return

        if (
            "amenity" in feature.tags
            or "shop" in feature.tags
            or "tourism" in feature.tags
        ):

            # Extract basic info
            name = feature.tags.get("name")
            if not name:
                return

            category = (
                feature.tags.get("amenity")
                or feature.tags.get("shop")
                or feature.tags.get("tourism")
            )
            amenity = feature.tags.get("amenity")

            # 1. Address
            addr_parts = []
            if feature.tags.get("addr:city"):
                addr_parts.append(feature.tags.get("addr:city"))
            if feature.tags.get("addr:district"):
                addr_parts.append(feature.tags.get("addr:district"))
            if feature.tags.get("addr:street"):
                addr_parts.append(feature.tags.get("addr:street"))
            if feature.tags.get("addr:housenumber"):
                addr_parts.append(feature.tags.get("addr:housenumber"))
            address = "".join(addr_parts) if addr_parts else "上海市"

            # AI Metadata Generation (Synchronous wrapper for async call)
            # In a real environment, we would use an async ingestion pipeline
            llm_data = asyncio.run(
                self.generate_ai_metadata(name, address, category, feature.tags)
            )

            # Location
            try:
                if feature_type == "node":
                    lat, lon = feature.location.lat, feature.location.lon
                else:
                    return
            except osmium.InvalidLocationError:
                return

            # Popularity
            pop_score = random.randint(0, 50)
            if "coffee" in name.lower() or "starbucks" in name.lower():
                pop_score += 40

            doc = {
                "_index": INDEX_NAME,
                "_source": {
                    "name": name,
                    "location": {"lat": lat, "lon": lon},
                    "category": category,
                    "amenity": amenity,
                    "tags": {k: v for k, v in feature.tags},
                    "popularity": min(100, pop_score),
                    "address": address,
                    # AI Fields
                    "keywords": llm_data.get("keywords", []),
                    "key_phrases": llm_data.get("key_phrases", []),
                    "key_info": llm_data.get("key_info", ""),
                    "rewrites": llm_data.get("rewrites", []),
                },
            }
            self.buffer.append(doc)
            self.count += 1
            logger.info(f"[{self.count}/{LIMIT}] Processed AI metadata for: {name}")

            if len(self.buffer) >= BATCH_SIZE:
                self.flush()

    async def generate_ai_metadata(self, name, address, category, tags):
        tags_str = ", ".join([f"{k}={v}" for k, v in tags])
        prompt = f"""
Analyze this POI in Shanghai:
Name: {name}
Category: {category}
Address: {address}
Tags: {tags_str}

Return ONLY a JSON object (no markdown, no explanation) with these fields:
"keywords": [3-5 specific words],
"key_phrases": [2-3 meaningful phrases],
"key_info": "a concise one-sentence description",
"rewrites": [3 search queries users might use to find this POI]
"""
        response = await remote_llm.generate(
            prompt, system_prompt="You are a data labeling expert. Output JSON ONLY."
        )
        try:
            # Simple JSON extraction in case there is some junk
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
        except Exception:
            logger.error(f"Failed to parse LLM response for {name}: {response}")

        return {}

    def flush(self):
        if self.buffer:
            success, _ = helpers.bulk(self.es, self.buffer)
            logger.info(f"Indexed {success} documents")
            self.buffer = []


def main():
    if not os.path.exists(OSM_FILE):
        logger.error(f"File {OSM_FILE} not found. Please download it from Geofabrik.")
        logger.info(
            "Example: wget https://download.geofabrik.de/asia/china/shanghai-latest.osm.pbf"
        )
        return

    handler = POIHandler()
    logger.info("Starting ingestion...")
    handler.apply_file(OSM_FILE)
    handler.flush()
    logger.info("Ingestion complete.")


if __name__ == "__main__":
    main()
