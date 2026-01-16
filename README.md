# DogFoodTracker-cce
A dog food tracker that tells you exactly how much to feed (home made) by Claude code


============================================================
====================== CLAUDE PROMPT =======================
============================================================

# Dog Meal Planner – Full Backend MVP

You are a senior full-stack engineer and data engineer. Build a production-quality MVP backend for a Dog Meal Planner application.

The app allows users to calculate precise dog meals (homemade + kibble + treats) using real nutrition data and real math.

------------------------------------------------------------
GOALS
------------------------------------------------------------

- Accurate calorie calculation per dog
- Ingredient-level nutrition using USDA FoodData Central API
- Optional brand food support (manual entry or OpenFoodFacts)
- Recipe builder with grams
- Nutrient aggregation and deficiency warnings vs AAFCO guidelines
- Clean, testable backend API

------------------------------------------------------------
TECH REQUIREMENTS
------------------------------------------------------------

- Backend: Node.js (Fastify/Express) OR Python (FastAPI)
- DB: SQLite (default) or Postgres
- External APIs:
  - USDA FoodData Central
  - Optional: OpenFoodFacts
- Focus on backend + correctness, not UI

------------------------------------------------------------
CORE MATH ENGINE
------------------------------------------------------------

RER:
RER = 70 × (weight_kg ^ 0.75)

MER:
MER = RER × factor

Factors:
- Neutered adult: 1.6
- Intact adult: 1.8
- Weight loss: 1.1
- Weight gain: 1.8
- Puppy: 2.0–3.0

Allocation:
target_kcal = MER
remaining_for_homemade = target_kcal - kibble_kcal - treats_kcal

kcal → grams:
grams = (desired_kcal / kcal_per_100g) × 100

Nutrient totals:
total = Σ(ingredient_grams × nutrient_per_100g / 100)

------------------------------------------------------------
NUTRIENTS TO TRACK (per 100g)
------------------------------------------------------------

- kcal
- protein (g)
- fat (g)
- carbs (g)
- calcium (mg)
- phosphorus (mg)
- iron (mg)
- zinc (mg)
- vitamin A (mcg)
- vitamin D (mcg)
- vitamin E (mg)

------------------------------------------------------------
AAFCO COMPARISON
------------------------------------------------------------

Table:

AAFCORequirement:
- nutrient
- min_per_1000kcal
- max_per_1000kcal (nullable)

Compute:
dog_intake_per_1000kcal = (total_nutrient / total_kcal) × 1000

Warn if below min or above max.

------------------------------------------------------------
DATA MODELS
------------------------------------------------------------

Dog:
- id
- name
- age_years
- sex
- neutered
- weight_kg
- target_weight_kg
- activity_level

Ingredient:
- id
- name
- source_type (USDA | BRAND | USER)
- source_id
- kcal_per_100g
- protein_g_per_100g
- fat_g_per_100g
- carbs_g_per_100g
- calcium_mg_per_100g
- phosphorus_mg_per_100g
- iron_mg_per_100g
- zinc_mg_per_100g
- vitamin_a_mcg_per_100g
- vitamin_d_mcg_per_100g
- vitamin_e_mg_per_100g

Recipe:
- id
- name
- meals_per_day

RecipeIngredient:
- recipe_id
- ingredient_id
- grams

FeedingPlan:
- dog_id
- recipe_id
- kibble_kcal
- treats_kcal
- homemade_kcal
- target_kcal

------------------------------------------------------------
EXTERNAL INTEGRATION
------------------------------------------------------------

USDA FoodData Central:
- Search foods
- Fetch by fdcId
- Normalize all nutrients to per-100g

------------------------------------------------------------
REST ENDPOINTS
------------------------------------------------------------

- POST /dog
- GET /dog/{id}
- GET /ingredient/search?q=...
- POST /ingredient/from-usda
- POST /ingredient/manual
- POST /recipe
- POST /recipe/{id}/ingredient
- POST /plan/compute

------------------------------------------------------------
/plan/compute RETURNS
------------------------------------------------------------

- target kcal
- kibble kcal
- treats kcal
- homemade kcal
- per-meal kcal
- per-ingredient grams per day
- per-ingredient grams per meal
- nutrient totals
- AAFCO warnings

------------------------------------------------------------
TESTING
------------------------------------------------------------

- RER/MER math
- kcal ↔ grams conversion
- nutrient aggregation
- AAFCO comparison

------------------------------------------------------------
DELIVERABLES
------------------------------------------------------------

- Full backend project
- DB schema
- Core calculation engine
- USDA integration service
- Seed data
- Example API calls
- README

------------------------------------------------------------
PRIORITY
------------------------------------------------------------

- Mathematical correctness
- Clean architecture
- Deterministic outputs
- Clarity over cleverness

------------------------------------------------------------
VERCEL DEPLOYMENT
------------------------------------------------------------

This project is configured for deployment on Vercel.

1. Connect your GitHub repository to Vercel

2. Set up a cloud PostgreSQL database:
   - Vercel Postgres
   - Neon (https://neon.tech)
   - Supabase (https://supabase.com)

3. Configure environment variables in Vercel:
   - DATABASE_URL: Your PostgreSQL connection string
   - USDA_API_KEY: Your USDA FoodData Central API key (optional)

4. Deploy! Vercel will automatically detect the Python configuration.

Note: SQLite is only suitable for local development. For production
deployment on Vercel, you must use a cloud database like PostgreSQL.
