"""Recipe API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import AuthUser, optional_auth
from app.models.models import Recipe, RecipeIngredient, Ingredient, IngredientType, FoodCategory
from app.schemas.schemas import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeIngredientAdd,
    RecipeIngredientResponse,
    IngredientType as IngredientTypeSchema,
    FoodCategory as FoodCategorySchema,
)

router = APIRouter(prefix="/recipe", tags=["recipes"])


@router.post("", response_model=RecipeResponse, status_code=201)
def create_recipe(
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    user: Optional[AuthUser] = Depends(optional_auth)
):
    """Create a new recipe."""
    db_recipe = Recipe(
        user_id=user.id if user else None,
        name=recipe.name,
        meals_per_day=recipe.meals_per_day,
    )
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return _recipe_to_response(db_recipe)


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: Optional[AuthUser] = Depends(optional_auth)
):
    """Get a recipe by ID with all ingredients."""
    query = db.query(Recipe).filter(Recipe.id == recipe_id)
    if user:
        query = query.filter((Recipe.user_id == user.id) | (Recipe.user_id.is_(None)))
    recipe = query.first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _recipe_to_response(recipe)


@router.post("/{recipe_id}/ingredient", response_model=RecipeResponse)
def add_ingredient_to_recipe(
    recipe_id: int,
    data: RecipeIngredientAdd,
    db: Session = Depends(get_db),
    user: Optional[AuthUser] = Depends(optional_auth)
):
    """Add an ingredient to a recipe."""
    query = db.query(Recipe).filter(Recipe.id == recipe_id)
    if user:
        query = query.filter((Recipe.user_id == user.id) | (Recipe.user_id.is_(None)))
    recipe = query.first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    ingredient = db.query(Ingredient).filter(Ingredient.id == data.ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    # Check if ingredient already in recipe
    existing = db.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == recipe_id,
        RecipeIngredient.ingredient_id == data.ingredient_id
    ).first()

    if existing:
        # Update percentage instead of adding duplicate
        existing.percentage = data.percentage
    else:
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe_id,
            ingredient_id=data.ingredient_id,
            percentage=data.percentage,
        )
        db.add(recipe_ingredient)

    db.commit()
    db.refresh(recipe)
    return _recipe_to_response(recipe)


@router.delete("/{recipe_id}/ingredient/{ingredient_id}", response_model=RecipeResponse)
def remove_ingredient_from_recipe(
    recipe_id: int,
    ingredient_id: int,
    db: Session = Depends(get_db),
    user: Optional[AuthUser] = Depends(optional_auth)
):
    """Remove an ingredient from a recipe."""
    query = db.query(Recipe).filter(Recipe.id == recipe_id)
    if user:
        query = query.filter((Recipe.user_id == user.id) | (Recipe.user_id.is_(None)))
    recipe = query.first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    recipe_ingredient = db.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == recipe_id,
        RecipeIngredient.ingredient_id == ingredient_id
    ).first()

    if recipe_ingredient:
        db.delete(recipe_ingredient)
        db.commit()
        db.refresh(recipe)

    return _recipe_to_response(recipe)


@router.get("", response_model=list[RecipeResponse])
def list_recipes(
    db: Session = Depends(get_db),
    user: Optional[AuthUser] = Depends(optional_auth)
):
    """List all recipes for the current user."""
    query = db.query(Recipe)
    if user:
        query = query.filter((Recipe.user_id == user.id) | (Recipe.user_id.is_(None)))
    else:
        query = query.filter(Recipe.user_id.is_(None))
    recipes = query.all()
    return [_recipe_to_response(r) for r in recipes]


@router.put("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: int,
    recipe_update: RecipeUpdate,
    db: Session = Depends(get_db),
    user: Optional[AuthUser] = Depends(optional_auth)
):
    """Update a recipe."""
    query = db.query(Recipe).filter(Recipe.id == recipe_id)
    if user:
        query = query.filter((Recipe.user_id == user.id) | (Recipe.user_id.is_(None)))
    recipe = query.first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    update_data = recipe_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recipe, field, value)

    db.commit()
    db.refresh(recipe)
    return _recipe_to_response(recipe)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: Optional[AuthUser] = Depends(optional_auth)
):
    """Delete a recipe."""
    query = db.query(Recipe).filter(Recipe.id == recipe_id)
    if user:
        query = query.filter((Recipe.user_id == user.id) | (Recipe.user_id.is_(None)))
    recipe = query.first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Delete associated recipe ingredients first
    for ri in recipe.ingredients:
        db.delete(ri)

    db.delete(recipe)
    db.commit()
    return None


def _recipe_to_response(recipe: Recipe) -> RecipeResponse:
    """Convert Recipe model to response schema."""
    ingredients = []
    for ri in recipe.ingredients:
        ing = ri.ingredient
        ing_type = ing.ingredient_type or IngredientType.FOOD
        ing_category = ing.category or FoodCategory.OTHER
        ingredients.append(RecipeIngredientResponse(
            id=ri.id,
            ingredient_id=ri.ingredient_id,
            ingredient_name=ing.name,
            percentage=ri.percentage,
            kcal_per_100g=ing.kcal_per_100g,
            ingredient_type=IngredientTypeSchema(ing_type.value),
            category=FoodCategorySchema(ing_category.value),
        ))
    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        meals_per_day=recipe.meals_per_day,
        ingredients=ingredients,
    )
