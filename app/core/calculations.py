"""
Core math engine for dog meal planning calculations.

RER (Resting Energy Requirement): 70 × (weight_kg ^ 0.75)
MER (Maintenance Energy Requirement): RER × activity factor
"""

from typing import Optional
from dataclasses import dataclass


# Activity/life stage factors for MER calculation
ACTIVITY_FACTORS = {
    "neutered_adult": 1.6,
    "intact_adult": 1.8,
    "weight_loss": 1.1,
    "weight_gain": 1.8,
    "puppy_young": 3.0,  # Under 4 months
    "puppy_older": 2.0,  # 4+ months
}


@dataclass
class NutrientTotals:
    """Nutrient totals for a meal or recipe."""
    kcal: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carbs_g: float = 0
    calcium_mg: float = 0
    phosphorus_mg: float = 0
    iron_mg: float = 0
    zinc_mg: float = 0
    vitamin_a_mcg: float = 0
    vitamin_d_mcg: float = 0
    vitamin_e_mg: float = 0


def calculate_rer(weight_kg: float) -> float:
    """
    Calculate Resting Energy Requirement (RER).

    Formula: RER = 70 × (weight_kg ^ 0.75)

    Args:
        weight_kg: Dog's weight in kilograms

    Returns:
        RER in kcal/day
    """
    if weight_kg <= 0:
        raise ValueError("Weight must be positive")
    return 70 * (weight_kg ** 0.75)


def get_activity_factor(
    neutered: bool,
    age_years: float,
    target_weight_kg: Optional[float] = None,
    current_weight_kg: Optional[float] = None
) -> float:
    """
    Determine the appropriate activity factor for MER calculation.

    Args:
        neutered: Whether the dog is neutered/spayed
        age_years: Dog's age in years
        target_weight_kg: Target weight (if different from current)
        current_weight_kg: Current weight

    Returns:
        Activity factor multiplier
    """
    # Check for puppy (under 1 year)
    if age_years < 1:
        if age_years < 4/12:  # Under 4 months
            return ACTIVITY_FACTORS["puppy_young"]
        return ACTIVITY_FACTORS["puppy_older"]

    # Check for weight management goals
    if target_weight_kg is not None and current_weight_kg is not None:
        if target_weight_kg < current_weight_kg:
            return ACTIVITY_FACTORS["weight_loss"]
        elif target_weight_kg > current_weight_kg:
            return ACTIVITY_FACTORS["weight_gain"]

    # Adult dogs
    if neutered:
        return ACTIVITY_FACTORS["neutered_adult"]
    return ACTIVITY_FACTORS["intact_adult"]


def calculate_mer(weight_kg: float, factor: float) -> float:
    """
    Calculate Maintenance Energy Requirement (MER).

    Formula: MER = RER × factor

    Args:
        weight_kg: Dog's weight in kilograms
        factor: Activity/life stage factor

    Returns:
        MER in kcal/day
    """
    rer = calculate_rer(weight_kg)
    return rer * factor


def calculate_homemade_kcal(
    target_kcal: float,
    kibble_kcal: float = 0,
    treats_kcal: float = 0
) -> float:
    """
    Calculate remaining calories for homemade food.

    Formula: remaining = target_kcal - kibble_kcal - treats_kcal

    Args:
        target_kcal: Total daily calorie target (MER)
        kibble_kcal: Calories from commercial kibble
        treats_kcal: Calories from treats

    Returns:
        Remaining kcal for homemade food
    """
    remaining = target_kcal - kibble_kcal - treats_kcal
    return max(0, remaining)


def kcal_to_grams(desired_kcal: float, kcal_per_100g: float) -> float:
    """
    Convert desired calories to grams of food.

    Formula: grams = (desired_kcal / kcal_per_100g) × 100

    Args:
        desired_kcal: Target calories from this ingredient
        kcal_per_100g: Caloric density of ingredient

    Returns:
        Grams needed to achieve desired calories
    """
    if kcal_per_100g <= 0:
        raise ValueError("kcal_per_100g must be positive")
    return (desired_kcal / kcal_per_100g) * 100


def grams_to_kcal(grams: float, kcal_per_100g: float) -> float:
    """
    Convert grams to calories.

    Formula: kcal = (grams / 100) × kcal_per_100g

    Args:
        grams: Amount of ingredient in grams
        kcal_per_100g: Caloric density of ingredient

    Returns:
        Calories from the given amount
    """
    return (grams / 100) * kcal_per_100g


def calculate_nutrient_amount(grams: float, nutrient_per_100g: float) -> float:
    """
    Calculate nutrient amount for a given weight of ingredient.

    Formula: amount = (grams × nutrient_per_100g) / 100

    Args:
        grams: Amount of ingredient in grams
        nutrient_per_100g: Nutrient amount per 100g

    Returns:
        Total nutrient amount
    """
    return (grams * nutrient_per_100g) / 100


def aggregate_nutrients(ingredients: list[dict]) -> NutrientTotals:
    """
    Aggregate nutrient totals from multiple ingredients.

    Args:
        ingredients: List of dicts with 'grams' and ingredient nutrient data

    Returns:
        NutrientTotals with summed values
    """
    totals = NutrientTotals()

    for ing in ingredients:
        grams = ing.get("grams", 0)
        totals.kcal += calculate_nutrient_amount(grams, ing.get("kcal_per_100g", 0))
        totals.protein_g += calculate_nutrient_amount(grams, ing.get("protein_g_per_100g", 0))
        totals.fat_g += calculate_nutrient_amount(grams, ing.get("fat_g_per_100g", 0))
        totals.carbs_g += calculate_nutrient_amount(grams, ing.get("carbs_g_per_100g", 0))
        totals.calcium_mg += calculate_nutrient_amount(grams, ing.get("calcium_mg_per_100g", 0))
        totals.phosphorus_mg += calculate_nutrient_amount(grams, ing.get("phosphorus_mg_per_100g", 0))
        totals.iron_mg += calculate_nutrient_amount(grams, ing.get("iron_mg_per_100g", 0))
        totals.zinc_mg += calculate_nutrient_amount(grams, ing.get("zinc_mg_per_100g", 0))
        totals.vitamin_a_mcg += calculate_nutrient_amount(grams, ing.get("vitamin_a_mcg_per_100g", 0))
        totals.vitamin_d_mcg += calculate_nutrient_amount(grams, ing.get("vitamin_d_mcg_per_100g", 0))
        totals.vitamin_e_mg += calculate_nutrient_amount(grams, ing.get("vitamin_e_mg_per_100g", 0))

    return totals


def nutrient_per_1000kcal(nutrient_amount: float, total_kcal: float) -> float:
    """
    Convert nutrient amount to per-1000kcal basis for AAFCO comparison.

    Formula: per_1000 = (nutrient_amount / total_kcal) × 1000

    Args:
        nutrient_amount: Total nutrient amount
        total_kcal: Total calories

    Returns:
        Nutrient amount per 1000 kcal
    """
    if total_kcal <= 0:
        return 0
    return (nutrient_amount / total_kcal) * 1000


def check_aafco_compliance(
    nutrient: str,
    amount_per_1000kcal: float,
    min_per_1000kcal: float,
    max_per_1000kcal: Optional[float] = None
) -> dict:
    """
    Check if a nutrient meets AAFCO requirements.

    Args:
        nutrient: Nutrient name
        amount_per_1000kcal: Actual intake per 1000 kcal
        min_per_1000kcal: AAFCO minimum
        max_per_1000kcal: AAFCO maximum (optional)

    Returns:
        Dict with status, warnings, and values
    """
    result = {
        "nutrient": nutrient,
        "amount_per_1000kcal": round(amount_per_1000kcal, 2),
        "min_required": min_per_1000kcal,
        "max_allowed": max_per_1000kcal,
        "status": "adequate",
        "warning": None
    }

    if amount_per_1000kcal < min_per_1000kcal:
        result["status"] = "deficient"
        result["warning"] = f"{nutrient} is below minimum ({amount_per_1000kcal:.2f} < {min_per_1000kcal})"
    elif max_per_1000kcal is not None and amount_per_1000kcal > max_per_1000kcal:
        result["status"] = "excess"
        result["warning"] = f"{nutrient} is above maximum ({amount_per_1000kcal:.2f} > {max_per_1000kcal})"

    return result


# =============================================================================
# Kibble / Hybrid Feeding Calculations
# =============================================================================

# Modified Atwater factors for pet food (kcal/g)
MODIFIED_ATWATER = {
    "protein": 3.5,
    "fat": 8.5,
    "carbs": 3.5,  # NFE
}

# Eggshell powder calcium content
EGGSHELL_CALCIUM_PCT = 38.0  # 38% calcium by weight


def calculate_kibble_nfe(
    protein_pct: float,
    fat_pct: float,
    fiber_pct: float,
    moisture_pct: float,
    ash_pct: float
) -> float:
    """
    Calculate Nitrogen-Free Extract (NFE) / Carbohydrates from kibble GA.

    Formula: NFE = 100 - (Protein% + Fat% + Fiber% + Moisture% + Ash%)

    Args:
        protein_pct: Crude Protein % from bag
        fat_pct: Crude Fat % from bag
        fiber_pct: Crude Fiber % from bag
        moisture_pct: Moisture % from bag
        ash_pct: Ash % from bag

    Returns:
        NFE percentage (carbohydrates)
    """
    nfe = 100 - (protein_pct + fat_pct + fiber_pct + moisture_pct + ash_pct)
    return max(0, nfe)


def calculate_kibble_nutrients(
    protein_pct: float,
    fat_pct: float,
    fiber_pct: float,
    moisture_pct: float,
    ash_pct: float,
    amount_grams: float,
    calcium_pct: Optional[float] = None,
    phosphorus_pct: Optional[float] = None
) -> dict:
    """
    Calculate actual nutrient amounts from kibble GA values.

    Uses Modified Atwater factors:
    - Protein: 3.5 kcal/g
    - Fat: 8.5 kcal/g
    - Carbs (NFE): 3.5 kcal/g

    Args:
        protein_pct: Crude Protein % from bag
        fat_pct: Crude Fat % from bag
        fiber_pct: Crude Fiber % from bag
        moisture_pct: Moisture % from bag
        ash_pct: Ash % from bag
        amount_grams: Kibble serving size in grams
        calcium_pct: Calcium % if listed on bag
        phosphorus_pct: Phosphorus % if listed on bag

    Returns:
        Dict with calculated nutrient values and kcal
    """
    # Calculate NFE (carbs)
    nfe_pct = calculate_kibble_nfe(protein_pct, fat_pct, fiber_pct, moisture_pct, ash_pct)

    # Convert percentages to actual grams based on serving size
    protein_g = (protein_pct / 100) * amount_grams
    fat_g = (fat_pct / 100) * amount_grams
    carbs_g = (nfe_pct / 100) * amount_grams
    fiber_g = (fiber_pct / 100) * amount_grams

    # Calculate kcal using Modified Atwater factors
    kcal = (
        protein_g * MODIFIED_ATWATER["protein"] +
        fat_g * MODIFIED_ATWATER["fat"] +
        carbs_g * MODIFIED_ATWATER["carbs"]
    )

    # Calculate minerals (convert % to mg)
    # % means g per 100g, so for amount_grams: (pct/100) * amount_grams * 1000 = mg
    calcium_mg = (calcium_pct / 100) * amount_grams * 1000 if calcium_pct else 0
    phosphorus_mg = (phosphorus_pct / 100) * amount_grams * 1000 if phosphorus_pct else 0

    return {
        "kcal": round(kcal, 2),
        "protein_g": round(protein_g, 2),
        "fat_g": round(fat_g, 2),
        "carbs_g": round(carbs_g, 2),
        "fiber_g": round(fiber_g, 2),
        "calcium_mg": round(calcium_mg, 2),
        "phosphorus_mg": round(phosphorus_mg, 2),
        "nfe_pct": round(nfe_pct, 2),
        "carb_pct_of_kibble": round(nfe_pct, 2),
    }


def analyze_ca_p_ratio(
    total_calcium_mg: float,
    total_phosphorus_mg: float,
    target_ratio: float = 1.2
) -> dict:
    """
    Analyze Calcium to Phosphorus ratio and provide recommendations.

    Target ratio: 1.2:1 (Ca:P)
    Warning threshold: < 1:1

    Args:
        total_calcium_mg: Combined calcium from all sources
        total_phosphorus_mg: Combined phosphorus from all sources
        target_ratio: Desired Ca:P ratio (default 1.2)

    Returns:
        Dict with ratio analysis and eggshell recommendation if needed
    """
    if total_phosphorus_mg <= 0:
        return {
            "total_calcium_mg": round(total_calcium_mg, 2),
            "total_phosphorus_mg": 0,
            "ca_p_ratio": 0,
            "status": "unknown",
            "calcium_gap_mg": None,
            "eggshell_recommendation_g": None,
            "message": "Cannot calculate ratio: no phosphorus data"
        }

    actual_ratio = total_calcium_mg / total_phosphorus_mg

    # Determine status and build response
    if actual_ratio >= 1.1 and actual_ratio <= 2.0:
        return {
            "total_calcium_mg": round(total_calcium_mg, 2),
            "total_phosphorus_mg": round(total_phosphorus_mg, 2),
            "ca_p_ratio": round(actual_ratio, 2),
            "status": "optimal",
            "calcium_gap_mg": None,
            "eggshell_recommendation_g": None,
            "message": f"Ca:P ratio is {actual_ratio:.2f}:1 - within optimal range (1.1-2.0:1)"
        }
    elif actual_ratio >= 1.0 and actual_ratio < 1.1:
        return {
            "total_calcium_mg": round(total_calcium_mg, 2),
            "total_phosphorus_mg": round(total_phosphorus_mg, 2),
            "ca_p_ratio": round(actual_ratio, 2),
            "status": "acceptable",
            "calcium_gap_mg": None,
            "eggshell_recommendation_g": None,
            "message": f"Ca:P ratio is {actual_ratio:.2f}:1 - acceptable but below optimal"
        }
    elif actual_ratio < 1.0:
        # Calculate calcium gap to reach 1:1 minimum
        calcium_needed_for_1_1 = total_phosphorus_mg * 1.0
        calcium_gap_mg = calcium_needed_for_1_1 - total_calcium_mg

        # Calculate eggshell powder recommendation (38% calcium)
        eggshell_g = calcium_gap_mg / (EGGSHELL_CALCIUM_PCT / 100 * 1000)

        return {
            "total_calcium_mg": round(total_calcium_mg, 2),
            "total_phosphorus_mg": round(total_phosphorus_mg, 2),
            "ca_p_ratio": round(actual_ratio, 2),
            "status": "low",
            "calcium_gap_mg": round(calcium_gap_mg, 2),
            "eggshell_recommendation_g": round(eggshell_g, 2),
            "message": f"Ca:P ratio is {actual_ratio:.2f}:1 - LOW. Add {eggshell_g:.1f}g eggshell powder"
        }
    else:  # ratio > 2.0
        return {
            "total_calcium_mg": round(total_calcium_mg, 2),
            "total_phosphorus_mg": round(total_phosphorus_mg, 2),
            "ca_p_ratio": round(actual_ratio, 2),
            "status": "high",
            "calcium_gap_mg": None,
            "eggshell_recommendation_g": None,
            "message": f"Ca:P ratio is {actual_ratio:.2f}:1 - above optimal, reduce calcium sources"
        }


def combine_nutrient_totals(kibble_nutrients: dict, fresh_totals: NutrientTotals) -> NutrientTotals:
    """
    Combine nutrients from kibble and fresh food sources.

    Args:
        kibble_nutrients: Dict from calculate_kibble_nutrients()
        fresh_totals: NutrientTotals from aggregate_nutrients()

    Returns:
        Combined NutrientTotals
    """
    return NutrientTotals(
        kcal=kibble_nutrients.get("kcal", 0) + fresh_totals.kcal,
        protein_g=kibble_nutrients.get("protein_g", 0) + fresh_totals.protein_g,
        fat_g=kibble_nutrients.get("fat_g", 0) + fresh_totals.fat_g,
        carbs_g=kibble_nutrients.get("carbs_g", 0) + fresh_totals.carbs_g,
        calcium_mg=kibble_nutrients.get("calcium_mg", 0) + fresh_totals.calcium_mg,
        phosphorus_mg=kibble_nutrients.get("phosphorus_mg", 0) + fresh_totals.phosphorus_mg,
        iron_mg=fresh_totals.iron_mg,  # Kibble GA doesn't include
        zinc_mg=fresh_totals.zinc_mg,
        vitamin_a_mcg=fresh_totals.vitamin_a_mcg,
        vitamin_d_mcg=fresh_totals.vitamin_d_mcg,
        vitamin_e_mg=fresh_totals.vitamin_e_mg,
    )
