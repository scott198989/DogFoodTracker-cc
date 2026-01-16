"""Tests for API endpoints."""

import pytest
from app.models.models import Ingredient, SourceType, AAFCORequirement


class TestDogEndpoints:
    """Tests for dog API endpoints."""

    def test_create_dog(self, client):
        """Test creating a dog."""
        response = client.post("/dog", json={
            "name": "Buddy",
            "age_years": 3,
            "sex": "male",
            "neutered": True,
            "weight_kg": 15,
            "activity_level": "moderate"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Buddy"
        assert data["weight_kg"] == 15
        assert data["id"] is not None

    def test_get_dog_with_calculations(self, client):
        """Test getting a dog with RER/MER calculations."""
        # Create dog first
        create_response = client.post("/dog", json={
            "name": "Max",
            "age_years": 5,
            "sex": "male",
            "neutered": True,
            "weight_kg": 20,
        })
        dog_id = create_response.json()["id"]

        # Get dog
        response = client.get(f"/dog/{dog_id}")
        assert response.status_code == 200
        data = response.json()
        assert "rer" in data
        assert "mer" in data
        assert "activity_factor" in data
        # Neutered adult factor should be 1.6
        assert data["activity_factor"] == 1.6
        # MER = RER * 1.6
        expected_rer = 70 * (20 ** 0.75)
        assert round(data["rer"], 1) == round(expected_rer, 1)

    def test_get_dog_not_found(self, client):
        """Test getting non-existent dog returns 404."""
        response = client.get("/dog/999")
        assert response.status_code == 404

    def test_list_dogs(self, client):
        """Test listing all dogs."""
        # Create two dogs
        client.post("/dog", json={
            "name": "Dog1", "age_years": 2, "sex": "male",
            "neutered": True, "weight_kg": 10
        })
        client.post("/dog", json={
            "name": "Dog2", "age_years": 3, "sex": "female",
            "neutered": False, "weight_kg": 15
        })

        response = client.get("/dog")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestIngredientEndpoints:
    """Tests for ingredient API endpoints."""

    def test_create_manual_ingredient(self, client):
        """Test creating a manual ingredient."""
        response = client.post("/ingredient/manual", json={
            "name": "Chicken Breast",
            "kcal_per_100g": 165,
            "protein_g_per_100g": 31,
            "fat_g_per_100g": 3.6,
            "carbs_g_per_100g": 0,
            "calcium_mg_per_100g": 15,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Chicken Breast"
        assert data["source_type"] == "USER"

    def test_get_ingredient(self, client):
        """Test getting an ingredient by ID."""
        # Create ingredient
        create_response = client.post("/ingredient/manual", json={
            "name": "Rice",
            "kcal_per_100g": 130,
        })
        ing_id = create_response.json()["id"]

        # Get ingredient
        response = client.get(f"/ingredient/{ing_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Rice"

    def test_list_ingredients(self, client):
        """Test listing all ingredients."""
        client.post("/ingredient/manual", json={
            "name": "Ingredient1", "kcal_per_100g": 100
        })
        client.post("/ingredient/manual", json={
            "name": "Ingredient2", "kcal_per_100g": 200
        })

        response = client.get("/ingredient")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestRecipeEndpoints:
    """Tests for recipe API endpoints."""

    def test_create_recipe(self, client):
        """Test creating a recipe."""
        response = client.post("/recipe", json={
            "name": "Chicken and Rice",
            "meals_per_day": 2
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Chicken and Rice"
        assert data["meals_per_day"] == 2

    def test_add_ingredient_to_recipe(self, client):
        """Test adding an ingredient to a recipe."""
        # Create ingredient
        ing_response = client.post("/ingredient/manual", json={
            "name": "Chicken", "kcal_per_100g": 165
        })
        ing_id = ing_response.json()["id"]

        # Create recipe
        recipe_response = client.post("/recipe", json={"name": "Test Recipe"})
        recipe_id = recipe_response.json()["id"]

        # Add ingredient to recipe
        response = client.post(f"/recipe/{recipe_id}/ingredient", json={
            "ingredient_id": ing_id,
            "grams": 100
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["ingredients"]) == 1
        assert data["ingredients"][0]["grams"] == 100

    def test_remove_ingredient_from_recipe(self, client):
        """Test removing an ingredient from a recipe."""
        # Create ingredient and recipe
        ing_response = client.post("/ingredient/manual", json={
            "name": "Beef", "kcal_per_100g": 250
        })
        ing_id = ing_response.json()["id"]

        recipe_response = client.post("/recipe", json={"name": "Test Recipe"})
        recipe_id = recipe_response.json()["id"]

        # Add then remove
        client.post(f"/recipe/{recipe_id}/ingredient", json={
            "ingredient_id": ing_id, "grams": 100
        })
        response = client.delete(f"/recipe/{recipe_id}/ingredient/{ing_id}")
        assert response.status_code == 200
        assert len(response.json()["ingredients"]) == 0


class TestPlanCompute:
    """Tests for feeding plan computation."""

    def test_compute_plan(self, client, db_session):
        """Test computing a complete feeding plan."""
        # Add AAFCO requirements
        db_session.add(AAFCORequirement(
            nutrient="protein",
            min_per_1000kcal=45000,
            max_per_1000kcal=None
        ))
        db_session.add(AAFCORequirement(
            nutrient="calcium",
            min_per_1000kcal=1250,
            max_per_1000kcal=6250
        ))
        db_session.commit()

        # Create dog
        dog_response = client.post("/dog", json={
            "name": "Buddy",
            "age_years": 3,
            "sex": "male",
            "neutered": True,
            "weight_kg": 15
        })
        dog_id = dog_response.json()["id"]

        # Create ingredients
        chicken_response = client.post("/ingredient/manual", json={
            "name": "Chicken",
            "kcal_per_100g": 165,
            "protein_g_per_100g": 31,
            "calcium_mg_per_100g": 15
        })
        chicken_id = chicken_response.json()["id"]

        rice_response = client.post("/ingredient/manual", json={
            "name": "Rice",
            "kcal_per_100g": 130,
            "protein_g_per_100g": 2.7,
            "calcium_mg_per_100g": 10
        })
        rice_id = rice_response.json()["id"]

        # Create recipe with ingredients
        recipe_response = client.post("/recipe", json={
            "name": "Test Recipe",
            "meals_per_day": 2
        })
        recipe_id = recipe_response.json()["id"]

        client.post(f"/recipe/{recipe_id}/ingredient", json={
            "ingredient_id": chicken_id, "grams": 150
        })
        client.post(f"/recipe/{recipe_id}/ingredient", json={
            "ingredient_id": rice_id, "grams": 100
        })

        # Compute plan
        response = client.post("/plan/compute", json={
            "dog_id": dog_id,
            "recipe_id": recipe_id,
            "kibble_kcal": 0,
            "treats_kcal": 50
        })

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "target_kcal" in data
        assert "homemade_kcal" in data
        assert "ingredient_portions" in data
        assert "nutrient_totals" in data
        assert "aafco_checks" in data

        # Verify calculations
        assert data["treats_kcal"] == 50
        assert data["homemade_kcal"] == data["target_kcal"] - 50
        assert data["meals_per_day"] == 2
        assert len(data["ingredient_portions"]) == 2

    def test_compute_plan_recipe_not_found(self, client):
        """Test compute plan with non-existent recipe."""
        # Create dog
        dog_response = client.post("/dog", json={
            "name": "Test",
            "age_years": 2,
            "sex": "male",
            "neutered": True,
            "weight_kg": 10
        })
        dog_id = dog_response.json()["id"]

        response = client.post("/plan/compute", json={
            "dog_id": dog_id,
            "recipe_id": 999
        })
        assert response.status_code == 404

    def test_compute_plan_empty_recipe(self, client):
        """Test compute plan with empty recipe returns error."""
        # Create dog
        dog_response = client.post("/dog", json={
            "name": "Test",
            "age_years": 2,
            "sex": "male",
            "neutered": True,
            "weight_kg": 10
        })
        dog_id = dog_response.json()["id"]

        # Create empty recipe
        recipe_response = client.post("/recipe", json={"name": "Empty"})
        recipe_id = recipe_response.json()["id"]

        response = client.post("/plan/compute", json={
            "dog_id": dog_id,
            "recipe_id": recipe_id
        })
        assert response.status_code == 400
        assert "no ingredients" in response.json()["detail"]


class TestHealthEndpoints:
    """Tests for health and root endpoints."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "endpoints" in data

    def test_health(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
