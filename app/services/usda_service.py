"""
USDA FoodData Central API integration service.

API Documentation: https://fdc.nal.usda.gov/api-guide.html
"""

import httpx
from typing import Optional

from app.core.config import settings


# Nutrient IDs from USDA FoodData Central
NUTRIENT_IDS = {
    "energy": 1008,           # kcal
    "protein": 1003,          # g
    "fat": 1004,              # g
    "carbs": 1005,            # g (Carbohydrate, by difference)
    "calcium": 1087,          # mg
    "phosphorus": 1091,       # mg
    "iron": 1089,             # mg
    "zinc": 1095,             # mg
    "vitamin_a": 1106,        # mcg RAE
    "vitamin_d": 1114,        # mcg (D2 + D3)
    "vitamin_e": 1109,        # mg (alpha-tocopherol)
}


class USDAService:
    """Service for interacting with USDA FoodData Central API."""

    def __init__(self):
        self.base_url = settings.USDA_BASE_URL
        self.api_key = settings.USDA_API_KEY

    async def search_foods(self, query: str, page_size: int = 25) -> dict:
        """
        Search for foods in USDA database.

        Args:
            query: Search term
            page_size: Number of results to return

        Returns:
            Search results with food items
        """
        url = f"{self.base_url}/foods/search"
        params = {
            "query": query,
            "pageSize": page_size,
            "dataType": ["Foundation", "SR Legacy"],
        }
        if self.api_key:
            params["api_key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_food_by_id(self, fdc_id: int) -> dict:
        """
        Get detailed food information by FDC ID.

        Args:
            fdc_id: USDA FoodData Central ID

        Returns:
            Detailed food data including nutrients
        """
        url = f"{self.base_url}/food/{fdc_id}"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def extract_nutrient(
        self,
        nutrients: list,
        nutrient_id: int,
        default: float = 0
    ) -> float:
        """
        Extract a specific nutrient value from USDA nutrient list.

        Args:
            nutrients: List of nutrient objects from USDA response
            nutrient_id: USDA nutrient ID to find
            default: Default value if not found

        Returns:
            Nutrient value per 100g
        """
        for nutrient in nutrients:
            nid = nutrient.get("nutrient", {}).get("id") or nutrient.get("nutrientId")
            if nid == nutrient_id:
                return nutrient.get("amount", default)
        return default

    def normalize_food_data(self, usda_food: dict) -> dict:
        """
        Normalize USDA food data to our ingredient format (per 100g).

        Args:
            usda_food: Raw USDA food data

        Returns:
            Normalized ingredient dict
        """
        nutrients = usda_food.get("foodNutrients", [])

        return {
            "name": usda_food.get("description", "Unknown Food"),
            "source_type": "USDA",
            "source_id": str(usda_food.get("fdcId")),
            "kcal_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["energy"]),
            "protein_g_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["protein"]),
            "fat_g_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["fat"]),
            "carbs_g_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["carbs"]),
            "calcium_mg_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["calcium"]),
            "phosphorus_mg_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["phosphorus"]),
            "iron_mg_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["iron"]),
            "zinc_mg_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["zinc"]),
            "vitamin_a_mcg_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["vitamin_a"]),
            "vitamin_d_mcg_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["vitamin_d"]),
            "vitamin_e_mg_per_100g": self.extract_nutrient(nutrients, NUTRIENT_IDS["vitamin_e"]),
        }

    def format_search_results(self, search_response: dict) -> list[dict]:
        """
        Format USDA search results for API response.

        Args:
            search_response: Raw USDA search response

        Returns:
            List of simplified food items
        """
        foods = search_response.get("foods", [])
        results = []

        for food in foods:
            results.append({
                "fdc_id": food.get("fdcId"),
                "description": food.get("description"),
                "data_type": food.get("dataType"),
                "brand_owner": food.get("brandOwner"),
            })

        return results


usda_service = USDAService()
