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


class IngredientCreate(IngredientBase):
    source_type: SourceType = SourceType.USER
    source_id: Optional[str] = None


class USDAIngredientCreate(BaseModel):
    fdc_id: int = Field(..., description="USDA FoodData Central ID")


class IngredientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
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


class IngredientResponse(IngredientBase):
    id: int
    source_type: SourceType
    source_id: Optional[str]

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
    grams: float = Field(..., gt=0)


class RecipeIngredientResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    grams: float

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
    grams_per_day: float
    grams_per_meal: float
    kcal_per_day: float
    total_grams_batch: float = Field(0, description="Total grams needed for entire batch")


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
    ingredient_portions: list[IngredientPortionResponse]
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
    new_grams: float = Field(..., ge=0)


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
