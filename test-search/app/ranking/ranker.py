from geopy.distance import geodesic
import math
from app.core.config import settings


class Ranker:
    def rank(
        self,
        candidates: list,
        user_lat: float,
        user_lon: float,
        sort_preference: str = "relevance",
    ):
        ranked_results = []

        max_score = max((c.get("es_score", 0) for c in candidates), default=1.0)
        if max_score == 0:
            max_score = 1.0

        for item in candidates:
            # 1. Normalize ES Score (Relevance)
            rel_score = item.get("es_score", 0) / max_score

            # 2. Distance Score (Decay)
            # Calculate distance in km
            item_lat = item["location"]["lat"]
            item_lon = item["location"]["lon"]
            dist_km = geodesic((user_lat, user_lon), (item_lat, item_lon)).km
            item["distance_km"] = dist_km

            # Simple Gaussian decay: exp(-dist^2 / 2sigma^2)
            sigma = settings.RANK_DIST_SIGMA
            dist_score = math.exp(-(dist_km**2) / (2 * (sigma**2)))

            # 3. Popularity Score (Log scale)
            pop = item.get("popularity", 0)
            max_pop = settings.RANK_POP_MAX
            pop_score = math.log1p(pop) / math.log1p(max_pop)  # Normalize 0-1

            # Final Weighted Score
            # Adjust weights based on user preference
            w_rel = settings.WEIGHT_REL
            w_dist = settings.WEIGHT_DIST
            w_pop = settings.WEIGHT_POP

            if sort_preference == "distance":
                w_dist = 0.8
                w_rel = 0.1
                w_pop = 0.1
            elif sort_preference == "popularity":
                w_pop = 0.8
                w_rel = 0.1
                w_dist = 0.1

            final_score = (
                (w_rel * rel_score) + (w_dist * dist_score) + (w_pop * pop_score)
            )
            item["final_score"] = final_score
            ranked_results.append(item)

        # Sort desc
        ranked_results.sort(key=lambda x: x["final_score"], reverse=True)
        return ranked_results[: settings.RANK_TOP_K]


ranker = Ranker()
