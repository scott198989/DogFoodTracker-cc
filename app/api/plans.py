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
    SimulateRequest,
    SimulateResponse,
    NutrientStatusResponse,
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

    # Validate percentages sum to ~100%
    total_percentage = sum(ri.percentage for ri in recipe.ingredients)
    if total_percentage < 99 or total_percentage > 101:
        raise HTTPException(
            status_code=400,
            detail=f"Recipe percentages must sum to 100% (currently {total_percentage:.1f}%)"
        )

    # Calculate target calories - use custom target if set, otherwise calculate MER
    factor = get_activity_factor(
        neutered=dog.neutered,
        age_years=dog.age_years,
        target_weight_kg=dog.target_weight_kg,
        current_weight_kg=dog.weight_kg
    )
    calculated_mer = calculate_mer(dog.weight_kg, factor)

    # Use dog's custom target_daily_kcal if set, otherwise use calculated MER
    target_kcal = dog.target_daily_kcal if dog.target_daily_kcal else calculated_mer

    homemade_kcal = calculate_homemade_kcal(
        target_kcal,
        request.kibble_kcal,
        request.treats_kcal
    )

    # Collect ingredient data with percentages
    ingredient_data = []
    for ri in recipe.ingredients:
        ing = ri.ingredient
        ingredient_data.append({
            "ingredient_id": ing.id,
            "ingredient_name": ing.name,
            "percentage": ri.percentage,
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

    # Calculate weighted average kcal per 100g of the mixed recipe
    # Formula: sum(percentage/100 * kcal_per_100g) for all ingredients
    weighted_avg_kcal_per_100g = sum(
        (ing["percentage"] / 100) * ing["kcal_per_100g"]
        for ing in ingredient_data
    )

    # Calculate total grams needed per day to hit calorie target
    # Formula: homemade_kcal / (weighted_avg_kcal_per_100g / 100)
    if weighted_avg_kcal_per_100g > 0:
        total_grams_per_day = (homemade_kcal / weighted_avg_kcal_per_100g) * 100
    else:
        total_grams_per_day = 0

    # Calculate batch totals
    num_days = request.num_days
    total_meals = recipe.meals_per_day * num_days
    total_batch_kcal = homemade_kcal * num_days
    total_batch_grams = total_grams_per_day * num_days

    # Calculate per-ingredient portions based on percentages
    ingredient_portions = []
    scaled_ingredients = []
    warnings = []

    # Safety limits for specific ingredients (grams per day)
    safety_limits = {
        "turmeric": 2,  # max 1-2g per day
        "liver": None,  # 5% of diet - calculated dynamically
        "coconut oil": None,  # 1 tbsp per 30 lbs - calculated based on dog weight
    }

    for ing_data in ingredient_data:
        # Calculate grams based on percentage
        grams_per_day = total_grams_per_day * (ing_data["percentage"] / 100)
        grams_per_meal = grams_per_day / recipe.meals_per_day
        kcal_per_day = grams_to_kcal(grams_per_day, ing_data["kcal_per_100g"])
        total_grams_batch = grams_per_day * num_days

        # Check safety limits
        ing_name_lower = ing_data["ingredient_name"].lower()

        # Turmeric limit
        if "turmeric" in ing_name_lower and grams_per_day > 2:
            warnings.append(f"⚠️ Turmeric exceeds safe limit: {grams_per_day:.1f}g/day (max 2g recommended)")

        # Liver limit (5% of diet)
        if "liver" in ing_name_lower and ing_data["percentage"] > 5:
            warnings.append(f"⚠️ Liver exceeds 5% of diet: {ing_data['percentage']:.1f}% (max 5% recommended)")

        # Coconut oil limit (1 tbsp = ~14g per 30 lbs body weight)
        if "coconut" in ing_name_lower and "oil" in ing_name_lower:
            dog_weight_lbs = dog.weight_kg * 2.205
            max_coconut_g = (dog_weight_lbs / 30) * 14
            if grams_per_day > max_coconut_g:
                warnings.append(f"⚠️ Coconut oil exceeds safe limit: {grams_per_day:.1f}g/day (max {max_coconut_g:.0f}g for {dog_weight_lbs:.0f} lb dog)")

        ingredient_portions.append(IngredientPortionResponse(
            ingredient_id=ing_data["ingredient_id"],
            ingredient_name=ing_data["ingredient_name"],
            grams_per_day=round(grams_per_day, 2),
            grams_per_meal=round(grams_per_meal, 2),
            kcal_per_day=round(kcal_per_day, 2),
            total_grams_batch=round(total_grams_batch, 2),
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

    # Calculate grams per container (per meal)
    grams_per_container = total_batch_grams / total_meals if total_meals > 0 else 0

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
        # Batch fields
        num_days=num_days,
        total_meals=total_meals,
        total_batch_kcal=round(total_batch_kcal, 2),
        total_batch_grams=round(total_batch_grams, 2),
        grams_per_container=round(grams_per_container, 2),
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


@router.post("/simulate", response_model=SimulateResponse)
def simulate_nutrition(
    request: SimulateRequest,
    db: Session = Depends(get_db)
):
    """
    Simulate nutritional impact of ingredient changes without saving.

    Allows users to see what happens if they adjust ingredient amounts
    in a recipe before committing changes.
    """
    # Get dog
    dog = db.query(Dog).filter(Dog.id == request.dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    # Get recipe with ingredients
    recipe = db.query(Recipe).filter(Recipe.id == request.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Build adjustment map (percentage adjustments)
    adjustment_map = {adj.ingredient_id: adj.new_percentage for adj in request.ingredient_adjustments}

    # Use 1000g as reference for nutrient calculations (makes percentages = grams × 10)
    reference_grams = 1000

    # Calculate BEFORE nutrients (original recipe percentages)
    before_ingredients = []
    for ri in recipe.ingredients:
        ing = ri.ingredient
        # Convert percentage to grams using reference
        grams = (ri.percentage / 100) * reference_grams
        before_ingredients.append({
            "grams": grams,
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

    before_totals = aggregate_nutrients(before_ingredients)

    # Calculate AFTER nutrients (with percentage adjustments)
    after_ingredients = []
    for ri in recipe.ingredients:
        ing = ri.ingredient
        new_percentage = adjustment_map.get(ing.id, ri.percentage)
        new_grams = (new_percentage / 100) * reference_grams
        after_ingredients.append({
            "grams": new_grams,
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

    after_totals = aggregate_nutrients(after_ingredients)

    # Get AAFCO requirements
    aafco_requirements = db.query(AAFCORequirement).all()

    # Calculate nutrient status
    nutrient_status = []
    warnings = []
    recommendations = []
    overall_worst = "excellent"

    status_order = {"excellent": 0, "good": 1, "caution": 2, "bad": 3, "dangerous": 4}
    color_map = {
        "excellent": "#10b981",
        "good": "#22c55e",
        "caution": "#eab308",
        "bad": "#f97316",
        "dangerous": "#ef4444"
    }

    if after_totals.kcal > 0:
        nutrient_mapping = {
            "protein": (after_totals.protein_g * 1000, "Protein"),
            "fat": (after_totals.fat_g * 1000, "Fat"),
            "calcium": (after_totals.calcium_mg, "Calcium"),
            "phosphorus": (after_totals.phosphorus_mg, "Phosphorus"),
            "iron": (after_totals.iron_mg, "Iron"),
            "zinc": (after_totals.zinc_mg, "Zinc"),
            "vitamin_a": (after_totals.vitamin_a_mcg, "Vitamin A"),
            "vitamin_d": (after_totals.vitamin_d_mcg, "Vitamin D"),
            "vitamin_e": (after_totals.vitamin_e_mg, "Vitamin E"),
        }

        for req in aafco_requirements:
            if req.nutrient not in nutrient_mapping:
                continue

            amount, display_name = nutrient_mapping[req.nutrient]
            per_1000 = nutrient_per_1000kcal(amount, after_totals.kcal)

            # Calculate percent of minimum
            pct_of_min = (per_1000 / req.min_per_1000kcal * 100) if req.min_per_1000kcal > 0 else 100
            pct_of_max = None
            if req.max_per_1000kcal:
                pct_of_max = (per_1000 / req.max_per_1000kcal * 100)

            # Determine status
            if per_1000 < req.min_per_1000kcal * 0.5:
                status = "bad"
                warnings.append(f"{display_name} is severely deficient ({pct_of_min:.0f}% of minimum)")
            elif per_1000 < req.min_per_1000kcal:
                status = "caution"
                warnings.append(f"{display_name} is below minimum ({pct_of_min:.0f}% of minimum)")
            elif req.max_per_1000kcal and per_1000 > req.max_per_1000kcal:
                status = "dangerous"
                warnings.append(f"{display_name} EXCEEDS SAFE LIMIT ({pct_of_max:.0f}% of maximum)")
            elif req.max_per_1000kcal and per_1000 > req.max_per_1000kcal * 0.8:
                status = "caution"
                warnings.append(f"{display_name} is approaching maximum limit")
            elif pct_of_min >= 100 and pct_of_min <= 150:
                status = "excellent"
            else:
                status = "good"

            # Track worst status
            if status_order[status] > status_order[overall_worst]:
                overall_worst = status

            nutrient_status.append(NutrientStatusResponse(
                nutrient=display_name,
                amount=round(per_1000, 2),
                percent_of_min=round(pct_of_min, 1),
                percent_of_max=round(pct_of_max, 1) if pct_of_max else None,
                status=status,
                color=color_map[status]
            ))

    # Generate recommendations
    for ns in nutrient_status:
        if ns.status == "bad":
            recommendations.append(f"Add more foods rich in {ns.nutrient.lower()}")
        elif ns.status == "dangerous":
            recommendations.append(f"REDUCE foods high in {ns.nutrient.lower()} immediately")

    return SimulateResponse(
        before=NutrientTotalsResponse(
            kcal=round(before_totals.kcal, 2),
            protein_g=round(before_totals.protein_g, 2),
            fat_g=round(before_totals.fat_g, 2),
            carbs_g=round(before_totals.carbs_g, 2),
            calcium_mg=round(before_totals.calcium_mg, 2),
            phosphorus_mg=round(before_totals.phosphorus_mg, 2),
            iron_mg=round(before_totals.iron_mg, 2),
            zinc_mg=round(before_totals.zinc_mg, 2),
            vitamin_a_mcg=round(before_totals.vitamin_a_mcg, 2),
            vitamin_d_mcg=round(before_totals.vitamin_d_mcg, 2),
            vitamin_e_mg=round(before_totals.vitamin_e_mg, 2),
        ),
        after=NutrientTotalsResponse(
            kcal=round(after_totals.kcal, 2),
            protein_g=round(after_totals.protein_g, 2),
            fat_g=round(after_totals.fat_g, 2),
            carbs_g=round(after_totals.carbs_g, 2),
            calcium_mg=round(after_totals.calcium_mg, 2),
            phosphorus_mg=round(after_totals.phosphorus_mg, 2),
            iron_mg=round(after_totals.iron_mg, 2),
            zinc_mg=round(after_totals.zinc_mg, 2),
            vitamin_a_mcg=round(after_totals.vitamin_a_mcg, 2),
            vitamin_d_mcg=round(after_totals.vitamin_d_mcg, 2),
            vitamin_e_mg=round(after_totals.vitamin_e_mg, 2),
        ),
        nutrient_status=nutrient_status,
        overall_status=overall_worst,
        warnings=warnings,
        recommendations=recommendations,
    )
