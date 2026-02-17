#!/bin/bash

# Load Configuration
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo ".env file not found! Using defaults."
    LOG_DIR="logs"
    LLM_PORT=8001
    APP_PORT=8000
    ES_HOST="http://localhost:9200"
fi

ES_URL=$ES_HOST
mkdir -p $LOG_DIR

# --- Data Ingestion ---

ingest_data() {
    echo "Checking dependencies for ingestion..."
    if ! curl -s $ES_URL > /dev/null; then
        echo "[ERROR] Elasticsearch is not reachable. Please run 'start' first."
        return 1
    fi
    if ! lsof -i:$LLM_PORT > /dev/null; then
        echo "[ERROR] LLM Service is not running. Please run 'start' first."
        return 1
    fi

    echo "Starting data ingestion (Shanghai OSM -> ES)..."
    uv run python scripts/ingest_shanghai.py
    echo "Ingestion process completed."
}

# --- Management ---

start_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "Docker is not running. Attempting to start Colima..."
        colima start
        # Wait for docker to be ready
        until docker info > /dev/null 2>&1; do
            echo "Waiting for Docker daemon..."
            sleep 2
        done
    else
        echo "Docker is already running."
    fi
}

start_es() {
    echo "Starting Elasticsearch & Kibana via Docker Compose..."
    docker-compose up -d
    # Stream logs to file (append mode)
    nohup docker-compose logs -f --no-color >> $LOG_DIR/$DOCKER_LOG_FILENAME 2>&1 &
    echo $! > $LOG_DIR/$DOCKER_PID_FILENAME
    
    echo "Waiting for Elasticsearch to be healthy..."
    until curl -s $ES_URL > /dev/null; do
        printf "."
        sleep 2
    done
    echo -e "\nElasticsearch is UP."
}

# --- Python Services ---

start_llm() {
    if lsof -Pi :$LLM_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "LLM Service already running on port $LLM_PORT."
    else
        echo "Starting LLM Model Service on $SERVICE_HOST:$LLM_PORT..."
        nohup uv run uvicorn app.llm_server:app --host $SERVICE_HOST --port $LLM_PORT >> $LOG_DIR/$LLM_LOG_FILENAME 2>&1 &
        echo "LLM Service started (PID: $!)."
    fi
}

start_search() {
    if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "Search Service already running on port $APP_PORT."
    else
        echo "Starting LBS Search Service on $SERVICE_HOST:$APP_PORT..."
        nohup uv run uvicorn app.main:app --host $SERVICE_HOST --port $APP_PORT >> $LOG_DIR/$APP_LOG_FILENAME 2>&1 &
        echo "Search Service started (PID: $!)."
    fi
}

# --- Management ---

stop_all() {
    echo "Stopping Python services..."
    lsof -ti:$LLM_PORT | xargs kill -9 2>/dev/null
    lsof -ti:$APP_PORT | xargs kill -9 2>/dev/null
    
    # Kill log streaming
    if [ -f $LOG_DIR/$DOCKER_PID_FILENAME ]; then
        kill $(cat $LOG_DIR/$DOCKER_PID_FILENAME) 2>/dev/null
        rm $LOG_DIR/$DOCKER_PID_FILENAME
    fi
    
    echo "Stopping Docker containers..."
    docker-compose down
    
    echo "Stopping Colima..."
    colima stop
}

check_status() {
    echo "--- System Status ---"
    # Docker
    if docker info > /dev/null 2>&1; then echo "[OK] Docker is running"; else echo "[FAIL] Docker is NOT running"; fi
    
    # ES
    if curl -s $ES_URL > /dev/null; then echo "[OK] Elasticsearch is accessible ($ES_URL)"; else echo "[FAIL] Elasticsearch is UNREACHABLE"; fi
    
    # Services
    if lsof -i:$LLM_PORT > /dev/null; then echo "[OK] LLM Service is running (Port $LLM_PORT)"; else echo "[FAIL] LLM Service is DOWN"; fi
    if lsof -i:$APP_PORT > /dev/null; then echo "[OK] Search Service is running (Port $APP_PORT)"; else echo "[FAIL] Search Service is DOWN"; fi
}

case "$1" in
    start)
        start_docker
        start_es
        start_llm
        echo "Waiting for LLM weights to load (approx ${WAIT_LLM_SECONDS}s)..."
        sleep $WAIT_LLM_SECONDS
        start_search
        echo "Full stack is starting up. Check status with: $0 status"
        ;;
    stop)
        stop_all
        ;;
    status)
        check_status
        ;;
    logs)
        tail -f $LOG_DIR/*.log
        ;;
    ingest)
        ingest_data
        ;;
    cleanup)
        echo "DANGER: Stopping all and clearing persistent ES data..."
        stop_all
        docker volume rm $(docker-compose config --volumes) 2>/dev/null
        rm -rf $LOG_DIR/*
        echo "Cleanup complete."
        ;;
    clean_logs)
        echo "Clearing all logs in $LOG_DIR..."
        rm -rf $LOG_DIR/*.log
        echo "Logs cleared."
        ;;
    *)
        echo "Usage: $0 {start|stop|status|logs|ingest|cleanup|clean_logs}"
        exit 1
esac
