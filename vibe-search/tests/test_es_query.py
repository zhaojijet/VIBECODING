from elasticsearch import Elasticsearch
import json
import requests


# Method 1: Python Client
def test_client():
    es = Elasticsearch("http://localhost:9200")
    print("\n--- Python Client Search ---")

    # Simple match query
    query = {"query": {"match": {"name": "coffee"}}, "size": 3}

    try:
        resp = es.search(index="poi_v1", body=query)
        print(f"Got {resp['hits']['total']['value']} hits.")
        for hit in resp["hits"]["hits"]:
            print(f"- {hit['_source']['name']} (Score: {hit['_score']})")
    except Exception as e:
        print(f"Error: {e}")


# Method 2: Raw HTTP Request (like curl)
def test_http():
    print("\n--- HTTP Request Search ---")
    url = "http://localhost:9200/poi_v1/_search"
    headers = {"Content-Type": "application/json"}
    data = {"query": {"term": {"category": "coffee"}}, "size": 3}

    try:
        resp = requests.get(url, headers=headers, json=data)
        if resp.status_code == 200:
            hits = resp.json()["hits"]["hits"]
            print(f"Got {len(hits)} hits (Term query).")
            for hit in hits:
                print(f"- {hit['_source']['name']}")
        else:
            print(f"Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_client()
    test_http()
