"""Pydantic schemas for request/response validation."""

from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class SourceType(str, Enum):
    USDA = "USDA"
    BRAND = "BRAND"
    USER = "USER"


# Dog schemas
class DogCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age_years: float = Field(..., gt=0, le=30)
    sex: Sex
    neutered: bool
    weight_kg: float = Field(..., gt=0, le=200)
    target_weight_kg: Optional[float] = Field(None, gt=0, le=200)
    activity_level: ActivityLevel = ActivityLevel.MODERATE


class DogResponse(BaseModel):
    id: int
    name: str
    age_years: float
    sex: Sex
    neutered: bool
    weight_kg: float
    target_weight_kg: Optional[float]
    activity_level: ActivityLevel

    class Config:
        from_attributes = True


class DogWithCalculations(DogResponse):
    rer: float
    mer: float
    activity_factor: float


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
    ingredient_portions: list[IngredientPortionResponse]
    nutrient_totals: NutrientTotalsResponse
    aafco_checks: list[AAFCOCheckResponse]
    warnings: list[str]
