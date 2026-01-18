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
    calculate_kibble_nutrients,
    analyze_ca_p_ratio,
    combine_nutrient_totals,
)
from app.models.models import Dog, Recipe, FeedingPlan, AAFCORequirement, IngredientType, FoodCategory
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
    CalorieBudgetResponse,
    IngredientType as IngredientTypeSchema,
    FoodCategory as FoodCategorySchema,
    HybridSimulateRequest,
    HybridSimulateResponse,
    HybridNutrientBreakdown,
    CaPRatioAnalysis,
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

    # Separate ingredients by type
    food_ingredients = []  # FOOD type - goes in batch
    oil_ingredients = []   # OIL type - added at mealtime
    supplement_ingredients = []  # SUPPLEMENT type - given separately
    treat_ingredients = []  # TREAT type - given separately

    for ri in recipe.ingredients:
        ing = ri.ingredient
        ing_data = {
            "ingredient_id": ing.id,
            "ingredient_name": ing.name,
            "percentage": ri.percentage,
            "ingredient_type": ing.ingredient_type or IngredientType.FOOD,
            "category": ing.category or FoodCategory.OTHER,
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
            # Type-specific fields
            "kcal_per_ml": ing.kcal_per_ml,
            "serving_size_ml": ing.serving_size_ml,
            "kcal_per_unit": ing.kcal_per_unit,
            "units_per_day": ing.units_per_day,
        }

        ing_type = ing.ingredient_type or IngredientType.FOOD
        if ing_type == IngredientType.FOOD:
            food_ingredients.append(ing_data)
        elif ing_type == IngredientType.OIL:
            oil_ingredients.append(ing_data)
        elif ing_type == IngredientType.SUPPLEMENT:
            supplement_ingredients.append(ing_data)
        elif ing_type == IngredientType.TREAT:
            treat_ingredients.append(ing_data)

    # Validate FOOD percentages sum to ~100% (only for food ingredients)
    food_total_percentage = sum(ing["percentage"] for ing in food_ingredients)
    if food_ingredients and (food_total_percentage < 99 or food_total_percentage > 101):
        # Normalize to 100% if not exact
        for ing in food_ingredients:
            ing["percentage"] = (ing["percentage"] / food_total_percentage) * 100

    # Calculate kcal from oils, supplements, treats (these are subtracted from homemade budget)
    oils_kcal_per_day = 0
    for oil in oil_ingredients:
        if oil["kcal_per_ml"] and oil["serving_size_ml"]:
            oils_kcal_per_day += oil["kcal_per_ml"] * oil["serving_size_ml"]
        elif oil["kcal_per_100g"] and oil["serving_size_ml"]:
            # Approximate: oil is about 0.92g per ml
            oils_kcal_per_day += (oil["serving_size_ml"] * 0.92 / 100) * oil["kcal_per_100g"]

    supplements_kcal_per_day = 0
    for supp in supplement_ingredients:
        if supp["kcal_per_unit"] and supp["units_per_day"]:
            supplements_kcal_per_day += supp["kcal_per_unit"] * supp["units_per_day"]

    # Treats come from request, not recipe
    treats_kcal_per_day = request.treats_kcal

    # Calculate weighted average kcal per 100g of the mixed FOOD recipe only
    if food_ingredients:
        weighted_avg_kcal_per_100g = sum(
            (ing["percentage"] / 100) * ing["kcal_per_100g"]
            for ing in food_ingredients
        )
    else:
        weighted_avg_kcal_per_100g = 0

    # Actual homemade food kcal (subtract oils/supplements from budget)
    actual_batch_kcal = homemade_kcal - oils_kcal_per_day - supplements_kcal_per_day

    # Calculate total grams needed per day for FOOD type only
    if weighted_avg_kcal_per_100g > 0 and actual_batch_kcal > 0:
        total_grams_per_day = (actual_batch_kcal / weighted_avg_kcal_per_100g) * 100
    else:
        total_grams_per_day = 0

    # Calculate batch totals
    num_days = request.num_days
    total_meals = recipe.meals_per_day * num_days
    total_batch_kcal = homemade_kcal * num_days
    total_batch_grams = total_grams_per_day * num_days

    # Calculate per-ingredient portions based on type
    batch_ingredients = []  # FOOD type only
    oils = []  # OIL type
    supplements = []  # SUPPLEMENT type
    treats = []  # TREAT type
    ingredient_portions = []  # All combined (for backwards compatibility)
    scaled_ingredients = []  # For nutrient aggregation
    warnings = []

    # Process FOOD type ingredients (batch cooking)
    for ing_data in food_ingredients:
        grams_per_day = total_grams_per_day * (ing_data["percentage"] / 100)
        grams_per_meal = grams_per_day / recipe.meals_per_day
        kcal_per_day = grams_to_kcal(grams_per_day, ing_data["kcal_per_100g"])
        total_grams_batch = grams_per_day * num_days

        # Check safety limits
        ing_name_lower = ing_data["ingredient_name"].lower()

        if "turmeric" in ing_name_lower and grams_per_day > 2:
            warnings.append(f"⚠️ Turmeric exceeds safe limit: {grams_per_day:.1f}g/day (max 2g recommended)")

        if "liver" in ing_name_lower and ing_data["percentage"] > 5:
            warnings.append(f"⚠️ Liver exceeds 5% of diet: {ing_data['percentage']:.1f}% (max 5% recommended)")

        portion = IngredientPortionResponse(
            ingredient_id=ing_data["ingredient_id"],
            ingredient_name=ing_data["ingredient_name"],
            ingredient_type=IngredientTypeSchema.FOOD,
            category=FoodCategorySchema(ing_data["category"].value) if ing_data["category"] else FoodCategorySchema.OTHER,
            grams_per_day=round(grams_per_day, 2),
            grams_per_meal=round(grams_per_meal, 2),
            kcal_per_day=round(kcal_per_day, 2),
            total_grams_batch=round(total_grams_batch, 2),
        )
        batch_ingredients.append(portion)
        ingredient_portions.append(portion)

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

    # Process OIL type ingredients (added at mealtime)
    for oil_data in oil_ingredients:
        serving_ml = oil_data["serving_size_ml"] or 5  # Default 5ml (1 tsp)
        ml_per_day = serving_ml * recipe.meals_per_day
        ml_per_meal = serving_ml
        tsp_per_meal = ml_per_meal / 5  # 1 tsp = 5ml

        if oil_data["kcal_per_ml"]:
            kcal_per_day = oil_data["kcal_per_ml"] * ml_per_day
        else:
            # Approximate: oil is about 0.92g per ml
            kcal_per_day = (ml_per_day * 0.92 / 100) * oil_data["kcal_per_100g"]

        # Check coconut oil limit
        ing_name_lower = oil_data["ingredient_name"].lower()
        if "coconut" in ing_name_lower:
            dog_weight_lbs = dog.weight_kg * 2.205
            max_tsp = dog_weight_lbs / 30  # 1 tsp per 30 lbs
            if tsp_per_meal * recipe.meals_per_day > max_tsp:
                warnings.append(f"⚠️ Coconut oil may exceed safe limit for {dog_weight_lbs:.0f} lb dog")

        portion = IngredientPortionResponse(
            ingredient_id=oil_data["ingredient_id"],
            ingredient_name=oil_data["ingredient_name"],
            ingredient_type=IngredientTypeSchema.OIL,
            category=FoodCategorySchema.FATS,
            kcal_per_day=round(kcal_per_day, 2),
            ml_per_meal=round(ml_per_meal, 2),
            ml_per_day=round(ml_per_day, 2),
            tsp_per_meal=round(tsp_per_meal, 2),
        )
        oils.append(portion)
        ingredient_portions.append(portion)

    # Process SUPPLEMENT type ingredients (given separately)
    for supp_data in supplement_ingredients:
        units = supp_data["units_per_day"] or 1
        kcal_from_supp = (supp_data["kcal_per_unit"] or 0) * units

        portion = IngredientPortionResponse(
            ingredient_id=supp_data["ingredient_id"],
            ingredient_name=supp_data["ingredient_name"],
            ingredient_type=IngredientTypeSchema.SUPPLEMENT,
            category=FoodCategorySchema.SUPPLEMENTS,
            units_per_day=units,
            kcal_from_supplement=round(kcal_from_supp, 2),
            kcal_per_day=round(kcal_from_supp, 2),
        )
        supplements.append(portion)
        ingredient_portions.append(portion)

    # Process TREAT type ingredients (optional, separate)
    for treat_data in treat_ingredients:
        units = treat_data["units_per_day"] or 0
        kcal_from_treat = (treat_data["kcal_per_unit"] or 0) * units

        portion = IngredientPortionResponse(
            ingredient_id=treat_data["ingredient_id"],
            ingredient_name=treat_data["ingredient_name"],
            ingredient_type=IngredientTypeSchema.TREAT,
            category=FoodCategorySchema.OTHER,
            units_per_day=units,
            treat_kcal_budget=round(kcal_from_treat, 2),
            kcal_per_day=round(kcal_from_treat, 2),
        )
        treats.append(portion)
        ingredient_portions.append(portion)

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

    # Build calorie budget summary
    total_kcal_accounted = (
        actual_batch_kcal +
        request.kibble_kcal +
        oils_kcal_per_day +
        supplements_kcal_per_day +
        treats_kcal_per_day
    )

    calorie_budget = CalorieBudgetResponse(
        target_daily_kcal=round(target_kcal, 2),
        homemade_food_kcal=round(actual_batch_kcal, 2),
        kibble_kcal=round(request.kibble_kcal, 2),
        oils_kcal=round(oils_kcal_per_day, 2),
        supplements_kcal=round(supplements_kcal_per_day, 2),
        treats_kcal=round(treats_kcal_per_day, 2),
        total_kcal=round(total_kcal_accounted, 2),
        remaining_kcal=round(target_kcal - total_kcal_accounted, 2),
    )

    return PlanComputeResponse(
        dog_id=dog.id,
        dog_name=dog.name,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        target_kcal=round(target_kcal, 2),
        kibble_kcal=request.kibble_kcal,
        treats_kcal=request.treats_kcal,
        homemade_kcal=round(homemade_kcal, 2),
        per_meal_kcal=round(actual_batch_kcal / recipe.meals_per_day, 2),
        meals_per_day=recipe.meals_per_day,
        # Batch fields
        num_days=num_days,
        total_meals=total_meals,
        total_batch_kcal=round(actual_batch_kcal * num_days, 2),
        total_batch_grams=round(total_batch_grams, 2),
        grams_per_container=round(grams_per_container, 2),
        # Separated by type
        batch_ingredients=batch_ingredients,
        oils=oils,
        supplements=supplements,
        treats=treats,
        ingredient_portions=ingredient_portions,  # Backwards compatibility
        # Calorie budget
        calorie_budget=calorie_budget,
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


@router.post("/simulate", response_model=HybridSimulateResponse)
def simulate_nutrition(
    request: HybridSimulateRequest,
    db: Session = Depends(get_db)
):
    """
    Simulate nutritional impact of ingredient changes with optional kibble input.

    Supports:
    - Fresh-only recipes (kibble=None)
    - Hybrid kibble + fresh combinations
    - Ca:P ratio analysis with eggshell recommendations
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

    # Calculate AFTER nutrients (fresh food with percentage adjustments)
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

    fresh_totals = aggregate_nutrients(after_ingredients)

    # Initialize warnings and recommendations
    warnings = []
    recommendations = []

    # Process kibble if provided
    kibble_nutrients = None
    kibble_analysis = None
    kibble_response = None

    if request.kibble:
        kibble_nutrients = calculate_kibble_nutrients(
            protein_pct=request.kibble.protein_pct,
            fat_pct=request.kibble.fat_pct,
            fiber_pct=request.kibble.fiber_pct,
            moisture_pct=request.kibble.moisture_pct,
            ash_pct=request.kibble.ash_pct,
            amount_grams=request.kibble.amount_grams,
            calcium_pct=request.kibble.calcium_pct,
            phosphorus_pct=request.kibble.phosphorus_pct,
        )

        # Build kibble analysis
        kibble_analysis = {
            "carb_pct": kibble_nutrients["carb_pct_of_kibble"],
            "high_filler_flag": kibble_nutrients["carb_pct_of_kibble"] > 40,
            "kcal_from_kibble": kibble_nutrients["kcal"],
            "protein_g": kibble_nutrients["protein_g"],
            "fat_g": kibble_nutrients["fat_g"],
            "carbs_g": kibble_nutrients["carbs_g"],
        }

        # Flag high filler content
        if kibble_analysis["high_filler_flag"]:
            warnings.append(
                f"HIGH FILLER CONTENT: Kibble is {kibble_nutrients['carb_pct_of_kibble']:.0f}% carbs (NFE)"
            )

        # Build kibble response object
        kibble_response = NutrientTotalsResponse(
            kcal=kibble_nutrients["kcal"],
            protein_g=kibble_nutrients["protein_g"],
            fat_g=kibble_nutrients["fat_g"],
            carbs_g=kibble_nutrients["carbs_g"],
            calcium_mg=kibble_nutrients["calcium_mg"],
            phosphorus_mg=kibble_nutrients["phosphorus_mg"],
            iron_mg=0,
            zinc_mg=0,
            vitamin_a_mcg=0,
            vitamin_d_mcg=0,
            vitamin_e_mg=0,
        )

        # Combine kibble + fresh for total nutrients
        combined_totals = combine_nutrient_totals(kibble_nutrients, fresh_totals)
    else:
        combined_totals = fresh_totals

    # Analyze Ca:P ratio (always run on combined totals)
    ca_p_result = analyze_ca_p_ratio(
        combined_totals.calcium_mg,
        combined_totals.phosphorus_mg
    )

    ca_p_analysis = CaPRatioAnalysis(
        total_calcium_mg=ca_p_result["total_calcium_mg"],
        total_phosphorus_mg=ca_p_result["total_phosphorus_mg"],
        ca_p_ratio=ca_p_result["ca_p_ratio"],
        status=ca_p_result["status"],
        calcium_gap_mg=ca_p_result["calcium_gap_mg"],
        eggshell_recommendation_g=ca_p_result["eggshell_recommendation_g"],
        message=ca_p_result["message"],
    )

    # Add Ca:P warnings and recommendations
    if ca_p_result["status"] == "low":
        warnings.append(ca_p_result["message"])
        if ca_p_result["eggshell_recommendation_g"]:
            recommendations.append(
                f"Add {ca_p_result['eggshell_recommendation_g']:.1f}g eggshell powder to balance calcium"
            )

    # Get AAFCO requirements
    aafco_requirements = db.query(AAFCORequirement).all()

    # Calculate nutrient status (based on combined totals for AAFCO comparison)
    nutrient_status = []
    overall_worst = "excellent"

    status_order = {"excellent": 0, "good": 1, "caution": 2, "bad": 3, "dangerous": 4}
    color_map = {
        "excellent": "#10b981",
        "good": "#22c55e",
        "caution": "#eab308",
        "bad": "#f97316",
        "dangerous": "#ef4444"
    }

    if combined_totals.kcal > 0:
        nutrient_mapping = {
            "protein": (combined_totals.protein_g * 1000, "Protein"),
            "fat": (combined_totals.fat_g * 1000, "Fat"),
            "calcium": (combined_totals.calcium_mg, "Calcium"),
            "phosphorus": (combined_totals.phosphorus_mg, "Phosphorus"),
            "iron": (combined_totals.iron_mg, "Iron"),
            "zinc": (combined_totals.zinc_mg, "Zinc"),
            "vitamin_a": (combined_totals.vitamin_a_mcg, "Vitamin A"),
            "vitamin_d": (combined_totals.vitamin_d_mcg, "Vitamin D"),
            "vitamin_e": (combined_totals.vitamin_e_mg, "Vitamin E"),
        }

        for req in aafco_requirements:
            if req.nutrient not in nutrient_mapping:
                continue

            amount, display_name = nutrient_mapping[req.nutrient]
            per_1000 = nutrient_per_1000kcal(amount, combined_totals.kcal)

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

    # Generate additional recommendations based on nutrient status
    for ns in nutrient_status:
        if ns.status == "bad":
            recommendations.append(f"Add more foods rich in {ns.nutrient.lower()}")
        elif ns.status == "dangerous":
            recommendations.append(f"REDUCE foods high in {ns.nutrient.lower()} immediately")

    # Build response
    fresh_response = NutrientTotalsResponse(
        kcal=round(fresh_totals.kcal, 2),
        protein_g=round(fresh_totals.protein_g, 2),
        fat_g=round(fresh_totals.fat_g, 2),
        carbs_g=round(fresh_totals.carbs_g, 2),
        calcium_mg=round(fresh_totals.calcium_mg, 2),
        phosphorus_mg=round(fresh_totals.phosphorus_mg, 2),
        iron_mg=round(fresh_totals.iron_mg, 2),
        zinc_mg=round(fresh_totals.zinc_mg, 2),
        vitamin_a_mcg=round(fresh_totals.vitamin_a_mcg, 2),
        vitamin_d_mcg=round(fresh_totals.vitamin_d_mcg, 2),
        vitamin_e_mg=round(fresh_totals.vitamin_e_mg, 2),
    )

    combined_response = NutrientTotalsResponse(
        kcal=round(combined_totals.kcal, 2),
        protein_g=round(combined_totals.protein_g, 2),
        fat_g=round(combined_totals.fat_g, 2),
        carbs_g=round(combined_totals.carbs_g, 2),
        calcium_mg=round(combined_totals.calcium_mg, 2),
        phosphorus_mg=round(combined_totals.phosphorus_mg, 2),
        iron_mg=round(combined_totals.iron_mg, 2),
        zinc_mg=round(combined_totals.zinc_mg, 2),
        vitamin_a_mcg=round(combined_totals.vitamin_a_mcg, 2),
        vitamin_d_mcg=round(combined_totals.vitamin_d_mcg, 2),
        vitamin_e_mg=round(combined_totals.vitamin_e_mg, 2),
    )

    return HybridSimulateResponse(
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
        after=HybridNutrientBreakdown(
            kibble=kibble_response,
            fresh=fresh_response,
            combined=combined_response,
        ),
        nutrient_status=nutrient_status,
        overall_status=overall_worst,
        warnings=warnings,
        recommendations=recommendations,
        ca_p_analysis=ca_p_analysis,
        kibble_analysis=kibble_analysis,
    )
