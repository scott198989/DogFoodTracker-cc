"""Recipe API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Recipe, RecipeIngredient, Ingredient
from app.schemas.schemas import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeIngredientAdd,
    RecipeIngredientResponse,
)

router = APIRouter(prefix="/recipe", tags=["recipes"])


@router.post("", response_model=RecipeResponse, status_code=201)
def create_recipe(recipe: RecipeCreate, db: Session = Depends(get_db)):
    """Create a new recipe."""
    db_recipe = Recipe(
        name=recipe.name,
        meals_per_day=recipe.meals_per_day,
    )
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return _recipe_to_response(db_recipe)


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Get a recipe by ID with all ingredients."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _recipe_to_response(recipe)


@router.post("/{recipe_id}/ingredient", response_model=RecipeResponse)
def add_ingredient_to_recipe(
    recipe_id: int,
    data: RecipeIngredientAdd,
    db: Session = Depends(get_db)
):
    """Add an ingredient to a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
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
    db: Session = Depends(get_db)
):
    """Remove an ingredient from a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
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
def list_recipes(db: Session = Depends(get_db)):
    """List all recipes."""
    recipes = db.query(Recipe).all()
    return [_recipe_to_response(r) for r in recipes]


@router.put("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: int,
    recipe_update: RecipeUpdate,
    db: Session = Depends(get_db)
):
    """Update a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    update_data = recipe_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recipe, field, value)

    db.commit()
    db.refresh(recipe)
    return _recipe_to_response(recipe)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Delete a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
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
        ingredients.append(RecipeIngredientResponse(
            id=ri.id,
            ingredient_id=ri.ingredient_id,
            ingredient_name=ri.ingredient.name,
            percentage=ri.percentage,
            kcal_per_100g=ri.ingredient.kcal_per_100g,
        ))
    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        meals_per_day=recipe.meals_per_day,
        ingredients=ingredients,
    )
