from pydantic import BaseModel
from typing import List, Optional


class SearchRequest(BaseModel):
    query: str
    lat: float
    lon: float
    radius_km: Optional[float] = 5.0


class POIResult(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    distance_km: float
    popularity: int
    score: float


class SearchResponse(BaseModel):
    intent: dict
    rewrites: List[str]
    results: List[POIResult]
