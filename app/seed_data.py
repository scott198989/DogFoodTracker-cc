"""
Seed data for the Dog Meal Planner database.

Includes:
- AAFCO nutrient requirements for adult dogs
- Sample ingredients with realistic nutrition data
- Sample recipes
"""

from app.core.database import SessionLocal, engine, Base
from app.models.models import AAFCORequirement, Ingredient, Recipe, RecipeIngredient, SourceType


def seed_aafco_requirements(db):
    """Seed AAFCO nutrient requirements for adult dog maintenance.

    Values are per 1000 kcal metabolizable energy.
    Source: AAFCO Dog Food Nutrient Profiles (2023)
    """
    requirements = [
        # Protein and Fat (converted to mg for consistency)
        {"nutrient": "protein", "min_per_1000kcal": 45000, "max_per_1000kcal": None},  # 45g min
        {"nutrient": "fat", "min_per_1000kcal": 13750, "max_per_1000kcal": None},      # 13.75g min
        # Minerals (mg)
        {"nutrient": "calcium", "min_per_1000kcal": 1250, "max_per_1000kcal": 6250},
        {"nutrient": "phosphorus", "min_per_1000kcal": 1000, "max_per_1000kcal": 4000},
        {"nutrient": "iron", "min_per_1000kcal": 10, "max_per_1000kcal": None},
        {"nutrient": "zinc", "min_per_1000kcal": 20, "max_per_1000kcal": None},
        # Vitamins
        {"nutrient": "vitamin_a", "min_per_1000kcal": 1250, "max_per_1000kcal": 62500},  # mcg
        {"nutrient": "vitamin_d", "min_per_1000kcal": 3.125, "max_per_1000kcal": 18.75}, # mcg
        {"nutrient": "vitamin_e", "min_per_1000kcal": 12.5, "max_per_1000kcal": None},   # mg
    ]

    for req_data in requirements:
        existing = db.query(AAFCORequirement).filter(
            AAFCORequirement.nutrient == req_data["nutrient"]
        ).first()
        if not existing:
            req = AAFCORequirement(**req_data)
            db.add(req)

    db.commit()
    print("AAFCO requirements seeded.")


def seed_sample_ingredients(db):
    """Seed sample ingredients with nutrition data.

    These are approximations based on USDA data for common dog food ingredients.
    """
    ingredients = [
        {
            "name": "Chicken Breast, cooked",
            "source_type": SourceType.USER,
            "source_id": "sample_chicken",
            "kcal_per_100g": 165,
            "protein_g_per_100g": 31,
            "fat_g_per_100g": 3.6,
            "carbs_g_per_100g": 0,
            "calcium_mg_per_100g": 15,
            "phosphorus_mg_per_100g": 196,
            "iron_mg_per_100g": 1.04,
            "zinc_mg_per_100g": 1.0,
            "vitamin_a_mcg_per_100g": 6,
            "vitamin_d_mcg_per_100g": 0.1,
            "vitamin_e_mg_per_100g": 0.27,
        },
        {
            "name": "Beef, ground, cooked",
            "source_type": SourceType.USER,
            "source_id": "sample_beef",
            "kcal_per_100g": 250,
            "protein_g_per_100g": 26,
            "fat_g_per_100g": 15,
            "carbs_g_per_100g": 0,
            "calcium_mg_per_100g": 18,
            "phosphorus_mg_per_100g": 175,
            "iron_mg_per_100g": 2.24,
            "zinc_mg_per_100g": 5.36,
            "vitamin_a_mcg_per_100g": 0,
            "vitamin_d_mcg_per_100g": 0.1,
            "vitamin_e_mg_per_100g": 0.14,
        },
        {
            "name": "Sweet Potato, cooked",
            "source_type": SourceType.USER,
            "source_id": "sample_sweet_potato",
            "kcal_per_100g": 90,
            "protein_g_per_100g": 2,
            "fat_g_per_100g": 0.1,
            "carbs_g_per_100g": 21,
            "calcium_mg_per_100g": 38,
            "phosphorus_mg_per_100g": 54,
            "iron_mg_per_100g": 0.69,
            "zinc_mg_per_100g": 0.32,
            "vitamin_a_mcg_per_100g": 961,
            "vitamin_d_mcg_per_100g": 0,
            "vitamin_e_mg_per_100g": 0.71,
        },
        {
            "name": "White Rice, cooked",
            "source_type": SourceType.USER,
            "source_id": "sample_rice",
            "kcal_per_100g": 130,
            "protein_g_per_100g": 2.7,
            "fat_g_per_100g": 0.3,
            "carbs_g_per_100g": 28,
            "calcium_mg_per_100g": 10,
            "phosphorus_mg_per_100g": 43,
            "iron_mg_per_100g": 0.2,
            "zinc_mg_per_100g": 0.49,
            "vitamin_a_mcg_per_100g": 0,
            "vitamin_d_mcg_per_100g": 0,
            "vitamin_e_mg_per_100g": 0.04,
        },
        {
            "name": "Beef Liver, cooked",
            "source_type": SourceType.USER,
            "source_id": "sample_liver",
            "kcal_per_100g": 175,
            "protein_g_per_100g": 29,
            "fat_g_per_100g": 5,
            "carbs_g_per_100g": 5,
            "calcium_mg_per_100g": 11,
            "phosphorus_mg_per_100g": 497,
            "iron_mg_per_100g": 6.54,
            "zinc_mg_per_100g": 5.3,
            "vitamin_a_mcg_per_100g": 9442,
            "vitamin_d_mcg_per_100g": 1.2,
            "vitamin_e_mg_per_100g": 0.38,
        },
        {
            "name": "Egg, whole, cooked",
            "source_type": SourceType.USER,
            "source_id": "sample_egg",
            "kcal_per_100g": 155,
            "protein_g_per_100g": 13,
            "fat_g_per_100g": 11,
            "carbs_g_per_100g": 1.1,
            "calcium_mg_per_100g": 50,
            "phosphorus_mg_per_100g": 172,
            "iron_mg_per_100g": 1.19,
            "zinc_mg_per_100g": 1.05,
            "vitamin_a_mcg_per_100g": 149,
            "vitamin_d_mcg_per_100g": 2.2,
            "vitamin_e_mg_per_100g": 1.03,
        },
        {
            "name": "Carrots, cooked",
            "source_type": SourceType.USER,
            "source_id": "sample_carrots",
            "kcal_per_100g": 35,
            "protein_g_per_100g": 0.8,
            "fat_g_per_100g": 0.2,
            "carbs_g_per_100g": 8,
            "calcium_mg_per_100g": 30,
            "phosphorus_mg_per_100g": 30,
            "iron_mg_per_100g": 0.34,
            "zinc_mg_per_100g": 0.2,
            "vitamin_a_mcg_per_100g": 852,
            "vitamin_d_mcg_per_100g": 0,
            "vitamin_e_mg_per_100g": 1.03,
        },
        {
            "name": "Green Beans, cooked",
            "source_type": SourceType.USER,
            "source_id": "sample_green_beans",
            "kcal_per_100g": 35,
            "protein_g_per_100g": 1.9,
            "fat_g_per_100g": 0.1,
            "carbs_g_per_100g": 8,
            "calcium_mg_per_100g": 44,
            "phosphorus_mg_per_100g": 38,
            "iron_mg_per_100g": 0.65,
            "zinc_mg_per_100g": 0.24,
            "vitamin_a_mcg_per_100g": 35,
            "vitamin_d_mcg_per_100g": 0,
            "vitamin_e_mg_per_100g": 0.41,
        },
    ]

    for ing_data in ingredients:
        existing = db.query(Ingredient).filter(
            Ingredient.source_id == ing_data["source_id"]
        ).first()
        if not existing:
            ing = Ingredient(**ing_data)
            db.add(ing)

    db.commit()
    print("Sample ingredients seeded.")


def seed_sample_recipe(db):
    """Seed a sample balanced recipe."""
    # Check if sample recipe exists
    existing = db.query(Recipe).filter(Recipe.name == "Balanced Chicken & Rice").first()
    if existing:
        print("Sample recipe already exists.")
        return

    # Get ingredients
    chicken = db.query(Ingredient).filter(Ingredient.source_id == "sample_chicken").first()
    rice = db.query(Ingredient).filter(Ingredient.source_id == "sample_rice").first()
    liver = db.query(Ingredient).filter(Ingredient.source_id == "sample_liver").first()
    sweet_potato = db.query(Ingredient).filter(Ingredient.source_id == "sample_sweet_potato").first()
    carrots = db.query(Ingredient).filter(Ingredient.source_id == "sample_carrots").first()

    if not all([chicken, rice, liver, sweet_potato, carrots]):
        print("Sample ingredients not found. Run seed_sample_ingredients first.")
        return

    # Create recipe
    recipe = Recipe(name="Balanced Chicken & Rice", meals_per_day=2)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)

    # Add ingredients (grams for a ~500 kcal daily portion as base)
    recipe_ingredients = [
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, grams=150),  # ~247 kcal
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=rice.id, grams=100),     # ~130 kcal
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=liver.id, grams=30),     # ~52 kcal (nutrient boost)
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=sweet_potato.id, grams=50),  # ~45 kcal
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=carrots.id, grams=50),   # ~17 kcal
    ]

    for ri in recipe_ingredients:
        db.add(ri)

    db.commit()
    print("Sample recipe seeded.")


def run_seed():
    """Run all seed functions."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_aafco_requirements(db)
        seed_sample_ingredients(db)
        seed_sample_recipe(db)
        print("Seed data complete!")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
