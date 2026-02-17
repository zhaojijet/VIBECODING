import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Logging
    LOG_DIR = os.getenv("LOG_DIR", "logs")

    # Elasticsearch
    ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
    ES_INDEX = os.getenv("ES_INDEX", "poi_v1")

    # Qwen / LLM
    LLM_PORT = int(os.getenv("LLM_PORT", "8001"))
    LLM_MODEL_PATH = os.getenv("LLM_MODEL_PATH", "data/models/Qwen3-0.6B-MLX-bf16")
    LLM_API_URL = os.getenv("LLM_API_URL", f"http://localhost:{LLM_PORT}/generate")
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # OpenAI compatible API (legacy support)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "LOCAL")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", f"http://localhost:{LLM_PORT}/v1")

    # Search Application
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    DEFAULT_RADIUS_KM = float(os.getenv("DEFAULT_RADIUS_KM", "5.0"))

    # Data
    OSM_DATA_PATH = os.getenv("OSM_DATA_PATH", "data/shanghai-latest.osm.pbf")
    TRACE_LOG_FILENAME = os.getenv("TRACE_LOG_FILENAME", "pipeline_trace.log")
    TRACE_LOG_PATH = os.path.join(LOG_DIR, TRACE_LOG_FILENAME)

    # Ranking Constants
    RANK_DIST_SIGMA = float(os.getenv("RANK_DIST_SIGMA", "2.0"))
    RANK_POP_MAX = int(os.getenv("RANK_POP_MAX", "100"))
    RANK_TOP_K = int(os.getenv("RANK_TOP_K", "10"))

    # Ranking Weights
    WEIGHT_REL = float(os.getenv("WEIGHT_REL", "0.5"))
    WEIGHT_DIST = float(os.getenv("WEIGHT_DIST", "0.3"))
    WEIGHT_POP = float(os.getenv("WEIGHT_POP", "0.2"))

    # Recall Boosts
    BOOST_PHRASE = float(os.getenv("BOOST_PHRASE", "5.0"))
    BOOST_KEYWORD = float(os.getenv("BOOST_KEYWORD", "2.0"))
    BOOST_INFO = float(os.getenv("BOOST_INFO", "1.5"))
    BOOST_NAME = float(os.getenv("BOOST_NAME", "1.5"))
    BOOST_ADDR = float(os.getenv("BOOST_ADDR", "1.2"))
    BOOST_REWRITE = float(os.getenv("BOOST_REWRITE", "1.2"))
    BOOST_CATEGORY = float(os.getenv("BOOST_CATEGORY", "2.0"))

    # Search & Dedup
    SEARCH_SIZE = int(os.getenv("SEARCH_SIZE", "10"))
    DEDUP_PRECISION = int(os.getenv("DEDUP_PRECISION", "3"))

    # Ingestion
    INGEST_BATCH_SIZE = int(os.getenv("INGEST_BATCH_SIZE", "10"))
    INGEST_LIMIT = int(os.getenv("INGEST_LIMIT", "5000"))

    # Orchestration & Infrastructure
    SERVICE_HOST = os.getenv("SERVICE_HOST", "127.0.0.1")
    WAIT_LLM_SECONDS = int(os.getenv("WAIT_LLM_SECONDS", "15"))
    DOCKER_LOG_FILENAME = os.getenv("DOCKER_LOG_FILENAME", "docker_compose.log")
    LLM_LOG_FILENAME = os.getenv("LLM_LOG_FILENAME", "llm_server.log")
    APP_LOG_FILENAME = os.getenv("APP_LOG_FILENAME", "search_app.log")
    DOCKER_PID_FILENAME = os.getenv("DOCKER_PID_FILENAME", "docker_logs.pid")


settings = Settings()
