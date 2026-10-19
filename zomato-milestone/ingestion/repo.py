"""Repository for loading, caching, and querying the restaurant catalog."""
import os
import re
import json
import logging
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd

from domain.models import Restaurant, Candidate
from ingestion.cleaner import clean_rating, clean_cost, clean_votes, normalize_text

logger = logging.getLogger(__name__)


class RestaurantRepo:
    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "restaurants.csv")
        self.restaurants: List[Restaurant] = []
        self._restaurant_dict: Dict[str, Restaurant] = {}
        self.p33_cost: float = 400.0
        self.p66_cost: float = 800.0
        self.load_catalog()

    def load_catalog(self):
        """Load catalog from local cache or seed dataset."""
        if os.path.exists(self.data_path):
            logger.info("Loading catalog from %s", self.data_path)
            try:
                df = pd.read_csv(self.data_path)
                self._load_from_df(df)
                return
            except Exception as e:
                logger.error("Failed to load %s: %s. Loading fallback seed.", self.data_path, e)
        
        # If cache file does not exist yet, load rich fallback seed catalog
        self._load_seed_catalog()

    def _load_from_df(self, df: pd.DataFrame):
        self.restaurants = []
        self._restaurant_dict = {}
        costs = []

        for idx, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            loc = str(row.get("location", "")).strip()
            cuisine = str(row.get("cuisine", "")).strip()
            cost = clean_cost(row.get("cost"))
            rating = clean_rating(str(row.get("rating")))
            if not name or not loc or not cuisine or cost is None or rating is None:
                continue

            rest_id = str(row.get("id", f"zom_{idx}"))
            rest = Restaurant(
                id=rest_id,
                name=name,
                location=loc,
                cuisine=cuisine,
                cost=cost,
                rating=rating,
                votes=clean_votes(row.get("votes")),
                address=str(row.get("address", "")) if pd.notna(row.get("address")) else None,
                online_order=str(row.get("online_order", "")) if pd.notna(row.get("online_order")) else None,
                table_booking=str(row.get("table_booking", "")) if pd.notna(row.get("table_booking")) else None,
                rest_type=str(row.get("rest_type", "")) if pd.notna(row.get("rest_type")) else None,
            )
            self.restaurants.append(rest)
            self._restaurant_dict[rest.id] = rest
            costs.append(cost)

        if costs:
            costs_series = pd.Series(costs)
            self.p33_cost = float(costs_series.quantile(0.33))
            self.p66_cost = float(costs_series.quantile(0.66))
            logger.info(
                "Catalog loaded: %d restaurants. Budget percentiles: P33=%.1f, P66=%.1f",
                len(self.restaurants),
                self.p33_cost,
                self.p66_cost,
            )

    def _load_seed_catalog(self):
        """Initial high-quality seed catalog representative of the Bangalore dataset."""
        seed_data = [
            {"id": "zom_1", "name": "Jalsa", "location": "Banashankari", "cuisine": "North Indian, Mughlai, Chinese", "cost": 800, "rating": 4.1, "votes": 775, "online_order": "Yes", "table_booking": "Yes", "rest_type": "Casual Dining", "address": "942, 21st Main Road, Banashankari"},
            {"id": "zom_2", "name": "Spice Elephant", "location": "Banashankari", "cuisine": "Chinese, North Indian, Thai", "cost": 800, "rating": 4.1, "votes": 787, "online_order": "Yes", "table_booking": "No", "rest_type": "Casual Dining", "address": "Banashankari 2nd Stage"},
            {"id": "zom_3", "name": "San Churro Cafe", "location": "Banashankari", "cuisine": "Cafe, Italian, Desserts", "cost": 800, "rating": 3.8, "votes": 918, "online_order": "Yes", "table_booking": "No", "rest_type": "Cafe", "address": "Banashankari 3rd Stage"},
            {"id": "zom_4", "name": "Addhuri Udupi Bhojana", "location": "Banashankari", "cuisine": "South Indian, North Indian", "cost": 300, "rating": 3.7, "votes": 88, "online_order": "No", "table_booking": "No", "rest_type": "Quick Bites", "address": "Banashankari BDA Complex"},
            {"id": "zom_5", "name": "Grand Village", "location": "Basavanagudi", "cuisine": "North Indian, Rajasthani, Gujarati", "cost": 600, "rating": 3.8, "votes": 166, "online_order": "No", "table_booking": "No", "rest_type": "Casual Dining", "address": "Basavanagudi, Bangalore"},
            {"id": "zom_6", "name": "Timepass Dinner", "location": "Basavanagudi", "cuisine": "North Indian", "cost": 600, "rating": 3.8, "votes": 338, "online_order": "Yes", "table_booking": "No", "rest_type": "Casual Dining", "address": "Basavanagudi, Bangalore"},
            {"id": "zom_7", "name": "Truffles", "location": "Koramangala", "cuisine": "Cafe, American, Burger, Italian", "cost": 900, "rating": 4.7, "votes": 14710, "online_order": "Yes", "table_booking": "No", "rest_type": "Cafe", "address": "5th Block, Koramangala"},
            {"id": "zom_8", "name": "Meghana Foods", "location": "Koramangala", "cuisine": "Biryani, Andhra, North Indian, Seafood", "cost": 600, "rating": 4.4, "votes": 8940, "online_order": "Yes", "table_booking": "No", "rest_type": "Casual Dining", "address": "Koramangala 1st Block"},
            {"id": "zom_9", "name": "Chianti", "location": "Koramangala", "cuisine": "Italian, Pizza, Pasta", "cost": 1500, "rating": 4.5, "votes": 3520, "online_order": "Yes", "table_booking": "Yes", "rest_type": "Fine Dining", "address": "5th Block, Koramangala"},
            {"id": "zom_10", "name": "Toit", "location": "Indiranagar", "cuisine": "Italian, American, Pizza, Continental", "cost": 1500, "rating": 4.8, "votes": 14950, "online_order": "Yes", "table_booking": "Yes", "rest_type": "Microbrewery", "address": "100 Feet Road, Indiranagar"},
            {"id": "zom_11", "name": "Empire Restaurant", "location": "Indiranagar", "cuisine": "North Indian, Mughlai, South Indian, Chinese", "cost": 750, "rating": 4.1, "votes": 4820, "online_order": "Yes", "table_booking": "No", "rest_type": "Casual Dining", "address": "Indiranagar, Bangalore"},
            {"id": "zom_12", "name": "Glen's Bakehouse", "location": "Indiranagar", "cuisine": "Bakery, Desserts, Italian, Cafe", "cost": 800, "rating": 4.4, "votes": 5210, "online_order": "Yes", "table_booking": "No", "rest_type": "Bakery, Cafe", "address": "Lavelle Road & Indiranagar"},
            {"id": "zom_13", "name": "Vidyarthi Bhavan", "location": "Basavanagudi", "cuisine": "South Indian", "cost": 200, "rating": 4.4, "votes": 4320, "online_order": "No", "table_booking": "No", "rest_type": "Quick Bites", "address": "Gandhi Bazaar, Basavanagudi"},
            {"id": "zom_14", "name": "Corner House Ice Cream", "location": "Koramangala", "cuisine": "Ice Cream, Desserts", "cost": 250, "rating": 4.6, "votes": 6120, "online_order": "Yes", "table_booking": "No", "rest_type": "Dessert Parlor", "address": "7th Block, Koramangala"},
            {"id": "zom_15", "name": "Windmills Craftworks", "location": "Whitefield", "cuisine": "Continental, American, North Indian", "cost": 2500, "rating": 4.6, "votes": 5420, "online_order": "No", "table_booking": "Yes", "rest_type": "Microbrewery", "address": "EPIP Zone, Whitefield"},
            {"id": "zom_16", "name": "Mainland China", "location": "Whitefield", "cuisine": "Chinese, Asian", "cost": 1700, "rating": 4.2, "votes": 1240, "online_order": "Yes", "table_booking": "Yes", "rest_type": "Casual Dining", "address": "ITPL Main Road, Whitefield"},
            {"id": "zom_17", "name": "The Black Pearl", "location": "Marathahalli", "cuisine": "North Indian, European, Mediterranean, BBQ", "cost": 1400, "rating": 4.7, "votes": 7180, "online_order": "Yes", "table_booking": "Yes", "rest_type": "Casual Dining", "address": "Outer Ring Road, Marathahalli"},
            {"id": "zom_18", "name": "Nagarjuna", "location": "Residency Road", "cuisine": "Andhra, South Indian, Biryani", "cost": 800, "rating": 4.3, "votes": 6120, "online_order": "Yes", "table_booking": "No", "rest_type": "Casual Dining", "address": "Residency Road, Bangalore"},
            {"id": "zom_19", "name": "Brahmin's Coffee Bar", "location": "Basavanagudi", "cuisine": "South Indian", "cost": 100, "rating": 4.8, "votes": 4650, "online_order": "No", "table_booking": "No", "rest_type": "Quick Bites", "address": "Shankarpuram, Basavanagudi"},
            {"id": "zom_20", "name": "Pasta Street", "location": "Indiranagar", "cuisine": "Italian, Pizza, Pasta", "cost": 1300, "rating": 4.4, "votes": 2840, "online_order": "Yes", "table_booking": "Yes", "rest_type": "Casual Dining", "address": "100 Feet Road, Indiranagar"},
            {"id": "zom_21", "name": "Udupi Grand", "location": "BTM", "cuisine": "South Indian, North Indian, Chinese", "cost": 350, "rating": 3.9, "votes": 420, "online_order": "Yes", "table_booking": "No", "rest_type": "Quick Bites", "address": "BTM 2nd Stage, Bangalore"},
            {"id": "zom_22", "name": "Onesta", "location": "Koramangala", "cuisine": "Pizza, Italian, Cafe, Desserts", "cost": 600, "rating": 4.3, "votes": 9120, "online_order": "Yes", "table_booking": "Yes", "rest_type": "Casual Dining", "address": "4th Block, Koramangala"},
            {"id": "zom_23", "name": "Fenny's Lounge & Kitchen", "location": "Koramangala", "cuisine": "Mediterranean, Pizza, Continental", "cost": 1600, "rating": 4.5, "votes": 4820, "online_order": "No", "table_booking": "Yes", "rest_type": "Lounge", "address": "7th Block, Koramangala"},
            {"id": "zom_24", "name": "Empire Sweets & Bakery", "location": "Shivajinagar", "cuisine": "Bakery, Desserts, Fast Food", "cost": 250, "rating": 3.8, "votes": 310, "online_order": "Yes", "table_booking": "No", "rest_type": "Bakery", "address": "Shivajinagar, Bangalore"},
            {"id": "zom_25", "name": "Sultans of Spice", "location": "Koramangala", "cuisine": "North Indian, Mughlai, Afghan", "cost": 1300, "rating": 4.2, "votes": 2400, "online_order": "Yes", "table_booking": "Yes", "rest_type": "Casual Dining", "address": "BluPetal Hotel, Koramangala"}
        ]
        df = pd.DataFrame(seed_data)
        self._load_from_df(df)

    def get_restaurant_by_id(self, rest_id: str) -> Optional[Restaurant]:
        return self._restaurant_dict.get(rest_id)

    def get_locations(self) -> List[str]:
        """Return unique sorted locations."""
        locs = set(r.location for r in self.restaurants if r.location)
        return sorted(list(locs))

    def get_cuisines(self) -> List[str]:
        """Return unique sorted individual cuisines."""
        cuisines = set()
        for r in self.restaurants:
            for item in r.cuisine.split(","):
                item_clean = item.strip()
                if item_clean:
                    cuisines.add(item_clean)
        return sorted(list(cuisines))

    def find_candidates(
        self,
        location: str,
        cuisine: str,
        min_cost: float,
        max_cost: float,
        min_rating: float = 3.0,
        limit: int = 15,
    ) -> List[Candidate]:
        """Filter catalog rows and return top candidates sorted by rating and votes."""
        loc_norm = normalize_text(location).lower()
        loc_clean = re.sub(r'[^a-z0-9]', '', loc_norm)
        city_aliases = {"bangalore", "bengaluru", "blr", "all", "any", "city", "karnataka", ""}
        is_city_wide = (loc_norm in city_aliases)

        cui_tokens = [t.strip().lower() for t in cuisine.split(",") if t.strip()]
        cui_clean_tokens = [re.sub(r'[^a-z0-9]', '', t) for t in cui_tokens if t]

        matches: List[Restaurant] = []
        for r in self.restaurants:
            # 1. Rating filter
            if r.rating < min_rating:
                continue

            # 2. Cost filter
            if r.cost < min_cost or r.cost > max_cost:
                continue

            # 3. Location filter
            if loc_clean and not is_city_wide:
                r_loc_clean = re.sub(r'[^a-z0-9]', '', r.location.lower())
                if loc_clean not in r_loc_clean and r_loc_clean not in loc_clean:
                    continue

            # 4. Cuisine filter (matches if any requested cuisine token appears in restaurant cuisine)
            if cui_clean_tokens:
                r_cui_clean = [re.sub(r'[^a-z0-9]', '', t) for t in r.cuisine.lower().split(",") if t.strip()]
                matched = False
                for tok in cui_clean_tokens:
                    if any(tok in rc or rc in tok for rc in r_cui_clean):
                        matched = True
                        break
                if not matched:
                    continue

            matches.append(r)

        # Sort by rating descending, then votes descending
        matches.sort(key=lambda x: (x.rating, x.votes), reverse=True)

        # Cap to top limit
        candidates = [
            Candidate(
                id=r.id,
                name=r.name,
                location=r.location,
                cuisine=r.cuisine,
                cost=r.cost,
                rating=r.rating,
                votes=r.votes,
                table_booking=r.table_booking,
                online_order=r.online_order,
                rest_type=r.rest_type,
            )
            for r in matches[:limit]
        ]
        return candidates
