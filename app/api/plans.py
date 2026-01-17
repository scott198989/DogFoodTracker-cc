"""Feeding plan API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.calculations import (
    calculate_rer,
    calculate_mer,
    get_activity_factor,
    calculate_homemade_kcal,
    grams_to_kcal,
    aggregate_nutrients,
    nutrient_per_1000kcal,
    check_aafco_compliance,
)
from app.models.models import Dog, Recipe, FeedingPlan, AAFCORequirement
from app.schemas.schemas import (
    PlanComputeRequest,
    PlanComputeResponse,
    FeedingPlanResponse,
    FeedingPlanUpdate,
    NutrientTotalsResponse,
    AAFCOCheckResponse,
    IngredientPortionResponse,
)

router = APIRouter(prefix="/plan", tags=["feeding plans"])


@router.post("/compute", response_model=PlanComputeResponse)
def compute_feeding_plan(
    request: PlanComputeRequest,
    db: Session = Depends(get_db)
):
    """
    Compute a complete feeding plan for a dog.

    Returns:
    - Target kcal based on dog's MER
    - Breakdown of calories (kibble, treats, homemade)
    - Per-meal and per-ingredient portions
    - Nutrient totals
    - AAFCO compliance warnings
    """
    # Get dog
    dog = db.query(Dog).filter(Dog.id == request.dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    # Get recipe with ingredients
    recipe = db.query(Recipe).filter(Recipe.id == request.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if not recipe.ingredients:
        raise HTTPException(status_code=400, detail="Recipe has no ingredients")

    # Calculate target calories
    factor = get_activity_factor(
        neutered=dog.neutered,
        age_years=dog.age_years,
        target_weight_kg=dog.target_weight_kg,
        current_weight_kg=dog.weight_kg
    )
    target_kcal = calculate_mer(dog.weight_kg, factor)
    homemade_kcal = calculate_homemade_kcal(
        target_kcal,
        request.kibble_kcal,
        request.treats_kcal
    )

    # Calculate recipe total calories
    recipe_total_kcal = 0
    ingredient_data = []
    for ri in recipe.ingredients:
        ing = ri.ingredient
        kcal = grams_to_kcal(ri.grams, ing.kcal_per_100g)
        recipe_total_kcal += kcal
        ingredient_data.append({
            "ingredient_id": ing.id,
            "ingredient_name": ing.name,
            "base_grams": ri.grams,
            "base_kcal": kcal,
            "kcal_per_100g": ing.kcal_per_100g,
            "protein_g_per_100g": ing.protein_g_per_100g,
            "fat_g_per_100g": ing.fat_g_per_100g,
            "carbs_g_per_100g": ing.carbs_g_per_100g,
            "calcium_mg_per_100g": ing.calcium_mg_per_100g,
            "phosphorus_mg_per_100g": ing.phosphorus_mg_per_100g,
            "iron_mg_per_100g": ing.iron_mg_per_100g,
            "zinc_mg_per_100g": ing.zinc_mg_per_100g,
            "vitamin_a_mcg_per_100g": ing.vitamin_a_mcg_per_100g,
            "vitamin_d_mcg_per_100g": ing.vitamin_d_mcg_per_100g,
            "vitamin_e_mg_per_100g": ing.vitamin_e_mg_per_100g,
        })

    # Scale recipe to match homemade kcal needs
    if recipe_total_kcal > 0:
        scale_factor = homemade_kcal / recipe_total_kcal
    else:
        scale_factor = 0

    # Calculate scaled portions
    ingredient_portions = []
    scaled_ingredients = []
    for ing_data in ingredient_data:
        grams_per_day = ing_data["base_grams"] * scale_factor
        grams_per_meal = grams_per_day / recipe.meals_per_day
        kcal_per_day = ing_data["base_kcal"] * scale_factor

        ingredient_portions.append(IngredientPortionResponse(
            ingredient_id=ing_data["ingredient_id"],
            ingredient_name=ing_data["ingredient_name"],
            grams_per_day=round(grams_per_day, 2),
            grams_per_meal=round(grams_per_meal, 2),
            kcal_per_day=round(kcal_per_day, 2),
        ))

        # Prepare for nutrient aggregation
        scaled_ingredients.append({
            "grams": grams_per_day,
            "kcal_per_100g": ing_data["kcal_per_100g"],
            "protein_g_per_100g": ing_data["protein_g_per_100g"],
            "fat_g_per_100g": ing_data["fat_g_per_100g"],
            "carbs_g_per_100g": ing_data["carbs_g_per_100g"],
            "calcium_mg_per_100g": ing_data["calcium_mg_per_100g"],
            "phosphorus_mg_per_100g": ing_data["phosphorus_mg_per_100g"],
            "iron_mg_per_100g": ing_data["iron_mg_per_100g"],
            "zinc_mg_per_100g": ing_data["zinc_mg_per_100g"],
            "vitamin_a_mcg_per_100g": ing_data["vitamin_a_mcg_per_100g"],
            "vitamin_d_mcg_per_100g": ing_data["vitamin_d_mcg_per_100g"],
            "vitamin_e_mg_per_100g": ing_data["vitamin_e_mg_per_100g"],
        })

    # Aggregate nutrients
    totals = aggregate_nutrients(scaled_ingredients)

    nutrient_totals = NutrientTotalsResponse(
        kcal=round(totals.kcal, 2),
        protein_g=round(totals.protein_g, 2),
        fat_g=round(totals.fat_g, 2),
        carbs_g=round(totals.carbs_g, 2),
        calcium_mg=round(totals.calcium_mg, 2),
        phosphorus_mg=round(totals.phosphorus_mg, 2),
        iron_mg=round(totals.iron_mg, 2),
        zinc_mg=round(totals.zinc_mg, 2),
        vitamin_a_mcg=round(totals.vitamin_a_mcg, 2),
        vitamin_d_mcg=round(totals.vitamin_d_mcg, 2),
        vitamin_e_mg=round(totals.vitamin_e_mg, 2),
    )

    # Check AAFCO compliance
    aafco_checks = []
    warnings = []
    aafco_requirements = db.query(AAFCORequirement).all()

    if totals.kcal > 0:
        nutrient_mapping = {
            "protein": totals.protein_g * 1000,  # Convert g to mg for consistency
            "fat": totals.fat_g * 1000,
            "calcium": totals.calcium_mg,
            "phosphorus": totals.phosphorus_mg,
            "iron": totals.iron_mg,
            "zinc": totals.zinc_mg,
            "vitamin_a": totals.vitamin_a_mcg,
            "vitamin_d": totals.vitamin_d_mcg,
            "vitamin_e": totals.vitamin_e_mg,
        }

        for req in aafco_requirements:
            nutrient_amount = nutrient_mapping.get(req.nutrient, 0)
            per_1000 = nutrient_per_1000kcal(nutrient_amount, totals.kcal)
            check = check_aafco_compliance(
                req.nutrient,
                per_1000,
                req.min_per_1000kcal,
                req.max_per_1000kcal
            )
            aafco_checks.append(AAFCOCheckResponse(**check))
            if check["warning"]:
                warnings.append(check["warning"])

    # Save feeding plan to database
    feeding_plan = FeedingPlan(
        dog_id=dog.id,
        recipe_id=recipe.id,
        kibble_kcal=request.kibble_kcal,
        treats_kcal=request.treats_kcal,
        homemade_kcal=round(homemade_kcal, 2),
        target_kcal=round(target_kcal, 2),
    )
    db.add(feeding_plan)
    db.commit()

    return PlanComputeResponse(
        dog_id=dog.id,
        dog_name=dog.name,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        target_kcal=round(target_kcal, 2),
        kibble_kcal=request.kibble_kcal,
        treats_kcal=request.treats_kcal,
        homemade_kcal=round(homemade_kcal, 2),
        per_meal_kcal=round(homemade_kcal / recipe.meals_per_day, 2),
        meals_per_day=recipe.meals_per_day,
        ingredient_portions=ingredient_portions,
        nutrient_totals=nutrient_totals,
        aafco_checks=aafco_checks,
        warnings=warnings,
    )


@router.get("", response_model=list[FeedingPlanResponse])
def list_feeding_plans(db: Session = Depends(get_db)):
    """List all saved feeding plans."""
    plans = db.query(FeedingPlan).all()
    return [_plan_to_response(p) for p in plans]


@router.get("/{plan_id}", response_model=FeedingPlanResponse)
def get_feeding_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get a specific feeding plan."""
    plan = db.query(FeedingPlan).filter(FeedingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Feeding plan not found")
    return _plan_to_response(plan)


@router.get("/dog/{dog_id}", response_model=list[FeedingPlanResponse])
def get_feeding_plans_for_dog(dog_id: int, db: Session = Depends(get_db)):
    """Get all feeding plans for a specific dog."""
    dog = db.query(Dog).filter(Dog.id == dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    plans = db.query(FeedingPlan).filter(FeedingPlan.dog_id == dog_id).all()
    return [_plan_to_response(p) for p in plans]


@router.put("/{plan_id}", response_model=FeedingPlanResponse)
def update_feeding_plan(
    plan_id: int,
    plan_update: FeedingPlanUpdate,
    db: Session = Depends(get_db)
):
    """Update a feeding plan's kibble and treat calories."""
    plan = db.query(FeedingPlan).filter(FeedingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Feeding plan not found")

    update_data = plan_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    # Recalculate homemade kcal
    plan.homemade_kcal = calculate_homemade_kcal(
        plan.target_kcal,
        plan.kibble_kcal,
        plan.treats_kcal
    )

    db.commit()
    db.refresh(plan)
    return _plan_to_response(plan)


@router.delete("/{plan_id}", status_code=204)
def delete_feeding_plan(plan_id: int, db: Session = Depends(get_db)):
    """Delete a feeding plan."""
    plan = db.query(FeedingPlan).filter(FeedingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Feeding plan not found")

    db.delete(plan)
    db.commit()
    return None


def _plan_to_response(plan: FeedingPlan) -> FeedingPlanResponse:
    """Convert FeedingPlan model to response schema."""
    return FeedingPlanResponse(
        id=plan.id,
        dog_id=plan.dog_id,
        dog_name=plan.dog.name,
        recipe_id=plan.recipe_id,
        recipe_name=plan.recipe.name,
        kibble_kcal=plan.kibble_kcal,
        treats_kcal=plan.treats_kcal,
        homemade_kcal=plan.homemade_kcal,
        target_kcal=plan.target_kcal,
    )
