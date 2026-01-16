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
