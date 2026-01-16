# Dog Meal Planner API - Example Calls

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload

# Seed the database with sample data
python -m app.seed_data
```

## API Endpoints

### 1. Create a Dog Profile

```bash
curl -X POST http://localhost:8000/dog \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Buddy",
    "age_years": 3,
    "sex": "male",
    "neutered": true,
    "weight_kg": 15,
    "activity_level": "moderate"
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "Buddy",
  "age_years": 3.0,
  "sex": "male",
  "neutered": true,
  "weight_kg": 15.0,
  "target_weight_kg": null,
  "activity_level": "moderate"
}
```

### 2. Get Dog with Calculated Energy Requirements

```bash
curl http://localhost:8000/dog/1
```

**Response:**
```json
{
  "id": 1,
  "name": "Buddy",
  "age_years": 3.0,
  "sex": "male",
  "neutered": true,
  "weight_kg": 15.0,
  "target_weight_kg": null,
  "activity_level": "moderate",
  "rer": 533.86,
  "mer": 854.18,
  "activity_factor": 1.6
}
```

### 3. Search USDA Foods

```bash
curl "http://localhost:8000/ingredient/search?q=chicken%20breast"
```

**Response:**
```json
[
  {
    "fdc_id": 171077,
    "description": "Chicken, breast, meat only, cooked, roasted",
    "data_type": "SR Legacy",
    "brand_owner": null
  }
]
```

### 4. Import Ingredient from USDA

```bash
curl -X POST http://localhost:8000/ingredient/from-usda \
  -H "Content-Type: application/json" \
  -d '{"fdc_id": 171077}'
```

### 5. Create Manual Ingredient

```bash
curl -X POST http://localhost:8000/ingredient/manual \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Brand X Kibble",
    "source_type": "BRAND",
    "kcal_per_100g": 350,
    "protein_g_per_100g": 25,
    "fat_g_per_100g": 15,
    "carbs_g_per_100g": 40,
    "calcium_mg_per_100g": 1200,
    "phosphorus_mg_per_100g": 1000
  }'
```

### 6. Create a Recipe

```bash
curl -X POST http://localhost:8000/recipe \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chicken and Rice Bowl",
    "meals_per_day": 2
  }'
```

### 7. Add Ingredients to Recipe

```bash
# Add chicken (ingredient_id=1)
curl -X POST http://localhost:8000/recipe/1/ingredient \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id": 1, "grams": 150}'

# Add rice (ingredient_id=2)
curl -X POST http://localhost:8000/recipe/1/ingredient \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id": 2, "grams": 100}'

# Add liver for nutrients (ingredient_id=3)
curl -X POST http://localhost:8000/recipe/1/ingredient \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id": 3, "grams": 30}'
```

### 8. Compute Feeding Plan

This is the main endpoint that calculates everything:

```bash
curl -X POST http://localhost:8000/plan/compute \
  -H "Content-Type: application/json" \
  -d '{
    "dog_id": 1,
    "recipe_id": 1,
    "kibble_kcal": 0,
    "treats_kcal": 50
  }'
```

**Response:**
```json
{
  "dog_id": 1,
  "dog_name": "Buddy",
  "recipe_id": 1,
  "recipe_name": "Balanced Chicken & Rice",
  "target_kcal": 854.18,
  "kibble_kcal": 0,
  "treats_kcal": 50,
  "homemade_kcal": 804.18,
  "per_meal_kcal": 402.09,
  "meals_per_day": 2,
  "ingredient_portions": [
    {
      "ingredient_id": 1,
      "ingredient_name": "Chicken Breast, cooked",
      "grams_per_day": 245.21,
      "grams_per_meal": 122.61,
      "kcal_per_day": 404.6
    },
    {
      "ingredient_id": 2,
      "ingredient_name": "White Rice, cooked",
      "grams_per_day": 163.47,
      "grams_per_meal": 81.74,
      "kcal_per_day": 212.51
    },
    {
      "ingredient_id": 3,
      "ingredient_name": "Beef Liver, cooked",
      "grams_per_day": 49.04,
      "grams_per_meal": 24.52,
      "kcal_per_day": 85.82
    }
  ],
  "nutrient_totals": {
    "kcal": 804.18,
    "protein_g": 94.52,
    "fat_g": 13.89,
    "carbs_g": 48.23,
    "calcium_mg": 45.12,
    "phosphorus_mg": 586.29,
    "iron_mg": 6.05,
    "zinc_mg": 5.76,
    "vitamin_a_mcg": 4779.15,
    "vitamin_d_mcg": 0.83,
    "vitamin_e_mg": 0.87
  },
  "aafco_checks": [
    {
      "nutrient": "protein",
      "amount_per_1000kcal": 117562.45,
      "min_required": 45000,
      "max_allowed": null,
      "status": "adequate",
      "warning": null
    },
    {
      "nutrient": "calcium",
      "amount_per_1000kcal": 56.11,
      "min_required": 1250,
      "max_allowed": 6250,
      "status": "deficient",
      "warning": "calcium is below minimum (56.11 < 1250)"
    }
  ],
  "warnings": [
    "calcium is below minimum (56.11 < 1250)"
  ]
}
```

## Full Workflow Example

```bash
# 1. Start fresh - seed the database
python -m app.seed_data

# 2. Create your dog
curl -X POST http://localhost:8000/dog \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Luna",
    "age_years": 2,
    "sex": "female",
    "neutered": true,
    "weight_kg": 12
  }'

# 3. Check available ingredients
curl http://localhost:8000/ingredient

# 4. Use the sample recipe (id=1 after seeding)
# Or create your own recipe

# 5. Compute the feeding plan
curl -X POST http://localhost:8000/plan/compute \
  -H "Content-Type: application/json" \
  -d '{
    "dog_id": 1,
    "recipe_id": 1,
    "kibble_kcal": 100,
    "treats_kcal": 30
  }'
```

## Interactive API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
