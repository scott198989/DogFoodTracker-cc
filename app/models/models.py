from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class Sex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class SourceType(str, enum.Enum):
    USDA = "USDA"
    BRAND = "BRAND"
    USER = "USER"


class Dog(Base):
    __tablename__ = "dogs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age_years = Column(Float, nullable=False)
    sex = Column(Enum(Sex), nullable=False)
    neutered = Column(Boolean, nullable=False)
    weight_kg = Column(Float, nullable=False)
    target_weight_kg = Column(Float, nullable=True)
    activity_level = Column(Enum(ActivityLevel), default=ActivityLevel.MODERATE)

    feeding_plans = relationship("FeedingPlan", back_populates="dog")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    source_type = Column(Enum(SourceType), nullable=False)
    source_id = Column(String, nullable=True)
    kcal_per_100g = Column(Float, nullable=False)
    protein_g_per_100g = Column(Float, default=0)
    fat_g_per_100g = Column(Float, default=0)
    carbs_g_per_100g = Column(Float, default=0)
    calcium_mg_per_100g = Column(Float, default=0)
    phosphorus_mg_per_100g = Column(Float, default=0)
    iron_mg_per_100g = Column(Float, default=0)
    zinc_mg_per_100g = Column(Float, default=0)
    vitamin_a_mcg_per_100g = Column(Float, default=0)
    vitamin_d_mcg_per_100g = Column(Float, default=0)
    vitamin_e_mg_per_100g = Column(Float, default=0)

    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    meals_per_day = Column(Integer, default=2)

    ingredients = relationship("RecipeIngredient", back_populates="recipe")
    feeding_plans = relationship("FeedingPlan", back_populates="recipe")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    grams = Column(Float, nullable=False)

    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")


class FeedingPlan(Base):
    __tablename__ = "feeding_plans"

    id = Column(Integer, primary_key=True, index=True)
    dog_id = Column(Integer, ForeignKey("dogs.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    kibble_kcal = Column(Float, default=0)
    treats_kcal = Column(Float, default=0)
    homemade_kcal = Column(Float, default=0)
    target_kcal = Column(Float, nullable=False)

    dog = relationship("Dog", back_populates="feeding_plans")
    recipe = relationship("Recipe", back_populates="feeding_plans")


class AAFCORequirement(Base):
    __tablename__ = "aafco_requirements"

    id = Column(Integer, primary_key=True, index=True)
    nutrient = Column(String, nullable=False, unique=True)
    min_per_1000kcal = Column(Float, nullable=False)
    max_per_1000kcal = Column(Float, nullable=True)
