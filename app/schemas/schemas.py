"""Pydantic schemas for request/response validation."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class LifeStage(str, Enum):
    PUPPY = "puppy"
    ADULT = "adult"
    SENIOR = "senior"


class SourceType(str, Enum):
    USDA = "USDA"
    BRAND = "BRAND"
    USER = "USER"


class IngredientType(str, Enum):
    FOOD = "food"           # Goes in batch (meats, veggies, grains)
    OIL = "oil"             # Added at mealtime, measured in mL/tsp
    SUPPLEMENT = "supplement"  # Chews/pills, given separately
    TREAT = "treat"         # Given separately, optional


class FoodCategory(str, Enum):
    PROTEIN = "protein"
    CARBS = "carbs"
    VEGETABLES = "vegetables"
    FRUITS = "fruits"
    FATS = "fats"
    SEEDS = "seeds"
    SUPPLEMENTS = "supplements"
    OTHER = "other"


class WeightUnit(str, Enum):
    KG = "kg"
    LBS = "lbs"


# Dog schemas
class DogCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    breed: Optional[str] = Field(None, max_length=100)
    age_years: float = Field(..., gt=0, le=30)
    sex: Sex
    neutered: bool
    weight_kg: float = Field(..., gt=0, le=200)
    target_weight_kg: Optional[float] = Field(None, gt=0, le=200)
    target_daily_kcal: Optional[float] = Field(None, gt=0, le=10000)
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    life_stage: LifeStage = LifeStage.ADULT
    notes: Optional[str] = None


class DogUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    breed: Optional[str] = Field(None, max_length=100)
    age_years: Optional[float] = Field(None, gt=0, le=30)
    sex: Optional[Sex] = None
    neutered: Optional[bool] = None
    weight_kg: Optional[float] = Field(None, gt=0, le=200)
    target_weight_kg: Optional[float] = Field(None, ge=0, le=200)  # Allow 0 to clear
    target_daily_kcal: Optional[float] = Field(None, ge=0, le=10000)  # Allow 0 to clear
    activity_level: Optional[ActivityLevel] = None
    life_stage: Optional[LifeStage] = None
    notes: Optional[str] = None


class DogResponse(BaseModel):
    id: int
    name: str
    breed: Optional[str]
    age_years: float
    sex: Sex
    neutered: bool
    weight_kg: float
    target_weight_kg: Optional[float]
    target_daily_kcal: Optional[float]
    activity_level: ActivityLevel
    life_stage: LifeStage
    notes: Optional[str]

    class Config:
        from_attributes = True


class DogWithCalculations(DogResponse):
    rer: float
    mer: float
    effective_daily_kcal: float  # Uses target_daily_kcal if set, otherwise MER
    activity_factor: float
    weight_status: str  # "at_target", "needs_loss", "needs_gain", or "no_target"


# Ingredient schemas
class IngredientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    ingredient_type: IngredientType = IngredientType.FOOD
    category: FoodCategory = FoodCategory.OTHER

    # Standard nutrition per 100g (for FOOD type)
    kcal_per_100g: float = Field(..., ge=0)
    protein_g_per_100g: float = Field(0, ge=0)
    fat_g_per_100g: float = Field(0, ge=0)
    carbs_g_per_100g: float = Field(0, ge=0)
    calcium_mg_per_100g: float = Field(0, ge=0)
    phosphorus_mg_per_100g: float = Field(0, ge=0)
    iron_mg_per_100g: float = Field(0, ge=0)
    zinc_mg_per_100g: float = Field(0, ge=0)
    vitamin_a_mcg_per_100g: float = Field(0, ge=0)
    vitamin_d_mcg_per_100g: float = Field(0, ge=0)
    vitamin_e_mg_per_100g: float = Field(0, ge=0)

    # For OIL type: measured in mL/tsp
    kcal_per_ml: Optional[float] = Field(None, ge=0)  # ~8.6 kcal/mL for most oils
    serving_size_ml: Optional[float] = Field(None, ge=0)  # Default serving in mL

    # For SUPPLEMENT/TREAT type: per-unit measurements
    kcal_per_unit: Optional[float] = Field(None, ge=0)  # kcal per chew/pill
    units_per_day: Optional[float] = Field(None, ge=0)  # Recommended daily units


class IngredientCreate(IngredientBase):
    source_type: SourceType = SourceType.USER
    source_id: Optional[str] = None


class USDAIngredientCreate(BaseModel):
    fdc_id: int = Field(..., description="USDA FoodData Central ID")


class IngredientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    ingredient_type: Optional[IngredientType] = None
    category: Optional[FoodCategory] = None
    kcal_per_100g: Optional[float] = Field(None, ge=0)
    protein_g_per_100g: Optional[float] = Field(None, ge=0)
    fat_g_per_100g: Optional[float] = Field(None, ge=0)
    carbs_g_per_100g: Optional[float] = Field(None, ge=0)
    calcium_mg_per_100g: Optional[float] = Field(None, ge=0)
    phosphorus_mg_per_100g: Optional[float] = Field(None, ge=0)
    iron_mg_per_100g: Optional[float] = Field(None, ge=0)
    zinc_mg_per_100g: Optional[float] = Field(None, ge=0)
    vitamin_a_mcg_per_100g: Optional[float] = Field(None, ge=0)
    vitamin_d_mcg_per_100g: Optional[float] = Field(None, ge=0)
    vitamin_e_mg_per_100g: Optional[float] = Field(None, ge=0)
    # Oil fields
    kcal_per_ml: Optional[float] = Field(None, ge=0)
    serving_size_ml: Optional[float] = Field(None, ge=0)
    # Supplement/Treat fields
    kcal_per_unit: Optional[float] = Field(None, ge=0)
    units_per_day: Optional[float] = Field(None, ge=0)


class IngredientResponse(BaseModel):
    id: int
    name: str
    source_type: SourceType
    source_id: Optional[str]
    ingredient_type: IngredientType
    category: FoodCategory
    # Standard nutrition per 100g
    kcal_per_100g: float
    protein_g_per_100g: float
    fat_g_per_100g: float
    carbs_g_per_100g: float
    calcium_mg_per_100g: float
    phosphorus_mg_per_100g: float
    iron_mg_per_100g: float
    zinc_mg_per_100g: float
    vitamin_a_mcg_per_100g: float
    vitamin_d_mcg_per_100g: float
    vitamin_e_mg_per_100g: float
    # Oil fields
    kcal_per_ml: Optional[float]
    serving_size_ml: Optional[float]
    # Supplement/Treat fields
    kcal_per_unit: Optional[float]
    units_per_day: Optional[float]

    class Config:
        from_attributes = True


class IngredientSearchResult(BaseModel):
    fdc_id: int
    description: str
    data_type: Optional[str]
    brand_owner: Optional[str]


# Recipe schemas
class RecipeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    meals_per_day: int = Field(2, ge=1, le=10)


class RecipeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    meals_per_day: Optional[int] = Field(None, ge=1, le=10)


class RecipeIngredientAdd(BaseModel):
    ingredient_id: int
    percentage: float = Field(..., gt=0, le=100, description="Percentage of recipe by weight (0-100)")


class RecipeIngredientResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    percentage: float
    kcal_per_100g: float = 0  # Include for UI display
    ingredient_type: IngredientType = IngredientType.FOOD
    category: FoodCategory = FoodCategory.OTHER

    class Config:
        from_attributes = True


class RecipeResponse(BaseModel):
    id: int
    name: str
    meals_per_day: int
    ingredients: list[RecipeIngredientResponse] = []

    class Config:
        from_attributes = True


# Feeding plan schemas
class PlanComputeRequest(BaseModel):
    dog_id: int
    recipe_id: int
    kibble_kcal: float = Field(0, ge=0)
    treats_kcal: float = Field(0, ge=0)
    num_days: int = Field(1, ge=1, le=30, description="Number of days to prep batch for")


class NutrientTotalsResponse(BaseModel):
    kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    calcium_mg: float
    phosphorus_mg: float
    iron_mg: float
    zinc_mg: float
    vitamin_a_mcg: float
    vitamin_d_mcg: float
    vitamin_e_mg: float


class AAFCOCheckResponse(BaseModel):
    nutrient: str
    amount_per_1000kcal: float
    min_required: float
    max_allowed: Optional[float]
    status: str
    warning: Optional[str]


class IngredientPortionResponse(BaseModel):
    ingredient_id: int
    ingredient_name: str
    ingredient_type: IngredientType = IngredientType.FOOD
    category: FoodCategory = FoodCategory.OTHER
    # For FOOD type (batch cooking)
    grams_per_day: float = 0
    grams_per_meal: float = 0
    kcal_per_day: float = 0
    total_grams_batch: float = Field(0, description="Total grams needed for entire batch")
    # For OIL type (added at mealtime)
    ml_per_meal: Optional[float] = None
    ml_per_day: Optional[float] = None
    tsp_per_meal: Optional[float] = None  # 1 tsp = ~5ml
    # For SUPPLEMENT type (given separately)
    units_per_day: Optional[float] = None
    kcal_from_supplement: Optional[float] = None
    # For TREAT type
    treat_kcal_budget: Optional[float] = None


class CalorieBudgetResponse(BaseModel):
    """Complete breakdown of daily calorie sources."""
    target_daily_kcal: float
    homemade_food_kcal: float
    kibble_kcal: float
    oils_kcal: float
    supplements_kcal: float
    treats_kcal: float
    total_kcal: float
    remaining_kcal: float  # Can be negative if over budget


class PlanComputeResponse(BaseModel):
    dog_id: int
    dog_name: str
    recipe_id: int
    recipe_name: str
    target_kcal: float
    kibble_kcal: float
    treats_kcal: float
    homemade_kcal: float
    per_meal_kcal: float
    meals_per_day: int
    # Batch planning fields
    num_days: int = Field(1, description="Number of days this batch covers")
    total_meals: int = Field(1, description="Total number of meal containers to prep")
    total_batch_kcal: float = Field(0, description="Total calories in entire batch")
    total_batch_grams: float = Field(0, description="Total grams of food in entire batch")
    grams_per_container: float = Field(0, description="Grams per meal container")
    # Separated by ingredient type
    batch_ingredients: list[IngredientPortionResponse] = []  # FOOD type only
    oils: list[IngredientPortionResponse] = []  # OIL type - added at mealtime
    supplements: list[IngredientPortionResponse] = []  # SUPPLEMENT type - given separately
    treats: list[IngredientPortionResponse] = []  # TREAT type - given separately
    # Legacy field for backwards compatibility
    ingredient_portions: list[IngredientPortionResponse] = []
    # Calorie budget
    calorie_budget: Optional[CalorieBudgetResponse] = None
    nutrient_totals: NutrientTotalsResponse
    aafco_checks: list[AAFCOCheckResponse]
    warnings: list[str]


# Feeding Plan stored response (for listing saved plans)
class FeedingPlanResponse(BaseModel):
    id: int
    dog_id: int
    dog_name: str
    recipe_id: int
    recipe_name: str
    kibble_kcal: float
    treats_kcal: float
    homemade_kcal: float
    target_kcal: float

    class Config:
        from_attributes = True


class FeedingPlanUpdate(BaseModel):
    kibble_kcal: Optional[float] = Field(None, ge=0)
    treats_kcal: Optional[float] = Field(None, ge=0)


# Weight Log schemas
class WeightLogCreate(BaseModel):
    dog_id: int
    weight_kg: float = Field(..., gt=0, le=200)
    notes: Optional[str] = None


class WeightLogResponse(BaseModel):
    id: int
    dog_id: int
    weight_kg: float
    logged_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


# Feeding Log schemas
class FeedingLogCreate(BaseModel):
    dog_id: int
    recipe_id: Optional[int] = None
    meal_type: Optional[str] = None  # breakfast, lunch, dinner, snack
    kcal_fed: float = Field(..., gt=0)
    notes: Optional[str] = None


class FeedingLogResponse(BaseModel):
    id: int
    dog_id: int
    recipe_id: Optional[int]
    recipe_name: Optional[str]
    meal_type: Optional[str]
    kcal_fed: float
    notes: Optional[str]
    logged_at: datetime

    class Config:
        from_attributes = True


# Daily summary
class DailySummary(BaseModel):
    date: str
    dog_id: int
    dog_name: str
    target_kcal: float
    total_kcal_fed: float
    remaining_kcal: float
    meals_logged: int
    on_track: bool


# Simulation schemas
class IngredientAdjustment(BaseModel):
    ingredient_id: int
    new_percentage: float = Field(..., ge=0, le=100, description="New percentage for this ingredient")


class SimulateRequest(BaseModel):
    dog_id: int
    recipe_id: int
    ingredient_adjustments: list[IngredientAdjustment]


class NutrientStatusResponse(BaseModel):
    nutrient: str
    amount: float
    percent_of_min: float
    percent_of_max: Optional[float] = None
    status: str  # "excellent", "good", "caution", "bad", "dangerous"
    color: str  # For UI display


class SimulateResponse(BaseModel):
    before: NutrientTotalsResponse
    after: NutrientTotalsResponse
    nutrient_status: list[NutrientStatusResponse]
    overall_status: str  # "excellent", "good", "caution", "bad", "dangerous"
    warnings: list[str]
    recommendations: list[str]


# Hybrid Feeding Schemas (Kibble + Fresh)
class KibbleInput(BaseModel):
    """Kibble Guaranteed Analysis from bag label."""
    protein_pct: float = Field(..., ge=0, le=100, description="Crude Protein %")
    fat_pct: float = Field(..., ge=0, le=100, description="Crude Fat %")
    fiber_pct: float = Field(..., ge=0, le=100, description="Crude Fiber %")
    moisture_pct: float = Field(10.0, ge=0, le=100, description="Moisture %")
    ash_pct: float = Field(7.0, ge=0, le=100, description="Ash %")
    calcium_pct: Optional[float] = Field(None, ge=0, le=10, description="Calcium % if listed")
    phosphorus_pct: Optional[float] = Field(None, ge=0, le=10, description="Phosphorus % if listed")
    amount_grams: float = Field(..., gt=0, description="Kibble serving size in grams")


class KibbleNutrients(BaseModel):
    """Calculated nutrients from kibble GA values."""
    kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fiber_g: float
    calcium_mg: float
    phosphorus_mg: float
    carb_pct_of_kibble: float


class CaPRatioAnalysis(BaseModel):
    """Calcium to Phosphorus ratio analysis."""
    total_calcium_mg: float
    total_phosphorus_mg: float
    ca_p_ratio: float
    status: str  # "optimal", "acceptable", "low", "high"
    calcium_gap_mg: Optional[float] = None
    eggshell_recommendation_g: Optional[float] = None
    message: str


class HybridNutrientBreakdown(BaseModel):
    """Breakdown of nutrients by source."""
    kibble: Optional[NutrientTotalsResponse] = None
    fresh: NutrientTotalsResponse
    combined: NutrientTotalsResponse


class HybridSimulateRequest(BaseModel):
    """Simulate request with optional kibble input."""
    dog_id: int
    recipe_id: int
    ingredient_adjustments: list[IngredientAdjustment]
    kibble: Optional[KibbleInput] = None


class HybridSimulateResponse(BaseModel):
    """Extended response with hybrid feeding data."""
    before: NutrientTotalsResponse
    after: HybridNutrientBreakdown
    nutrient_status: list[NutrientStatusResponse]
    overall_status: str
    warnings: list[str]
    recommendations: list[str]
    ca_p_analysis: Optional[CaPRatioAnalysis] = None
    kibble_analysis: Optional[dict] = None
