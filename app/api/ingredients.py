"""Ingredient API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Ingredient, SourceType
from app.schemas.schemas import (
    IngredientCreate,
    IngredientUpdate,
    IngredientResponse,
    USDAIngredientCreate,
    IngredientSearchResult,
)
from app.services.usda_service import usda_service

router = APIRouter(prefix="/ingredient", tags=["ingredients"])


@router.get("/search", response_model=list[IngredientSearchResult])
async def search_ingredients(
    q: str = Query(..., min_length=2, description="Search query")
):
    """
    Search for ingredients in USDA FoodData Central.

    Returns matching foods that can be imported using /ingredient/from-usda.
    """
    import httpx
    try:
        results = await usda_service.search_foods(q)
        return usda_service.format_search_results(results)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="USDA API timeout - try again")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"USDA API returned {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"USDA API error: {str(e)}")


@router.post("/from-usda", response_model=IngredientResponse, status_code=201)
async def create_ingredient_from_usda(
    data: USDAIngredientCreate,
    db: Session = Depends(get_db)
):
    """
    Create an ingredient from USDA FoodData Central.

    Fetches nutrition data from USDA and normalizes it to our format.
    """
    # Check if already imported
    existing = db.query(Ingredient).filter(
        Ingredient.source_type == SourceType.USDA,
        Ingredient.source_id == str(data.fdc_id)
    ).first()
    if existing:
        return existing

    try:
        usda_food = await usda_service.get_food_by_id(data.fdc_id)
        normalized = usda_service.normalize_food_data(usda_food)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"USDA API error: {str(e)}")

    db_ingredient = Ingredient(
        name=normalized["name"],
        source_type=SourceType.USDA,
        source_id=normalized["source_id"],
        kcal_per_100g=normalized["kcal_per_100g"],
        protein_g_per_100g=normalized["protein_g_per_100g"],
        fat_g_per_100g=normalized["fat_g_per_100g"],
        carbs_g_per_100g=normalized["carbs_g_per_100g"],
        calcium_mg_per_100g=normalized["calcium_mg_per_100g"],
        phosphorus_mg_per_100g=normalized["phosphorus_mg_per_100g"],
        iron_mg_per_100g=normalized["iron_mg_per_100g"],
        zinc_mg_per_100g=normalized["zinc_mg_per_100g"],
        vitamin_a_mcg_per_100g=normalized["vitamin_a_mcg_per_100g"],
        vitamin_d_mcg_per_100g=normalized["vitamin_d_mcg_per_100g"],
        vitamin_e_mg_per_100g=normalized["vitamin_e_mg_per_100g"],
    )
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    return db_ingredient


@router.post("/manual", response_model=IngredientResponse, status_code=201)
def create_manual_ingredient(
    ingredient: IngredientCreate,
    db: Session = Depends(get_db)
):
    """
    Create a manually entered ingredient.

    Use this for brand foods or custom ingredients not in USDA database.
    """
    db_ingredient = Ingredient(
        name=ingredient.name,
        source_type=ingredient.source_type.value,
        source_id=ingredient.source_id,
        kcal_per_100g=ingredient.kcal_per_100g,
        protein_g_per_100g=ingredient.protein_g_per_100g,
        fat_g_per_100g=ingredient.fat_g_per_100g,
        carbs_g_per_100g=ingredient.carbs_g_per_100g,
        calcium_mg_per_100g=ingredient.calcium_mg_per_100g,
        phosphorus_mg_per_100g=ingredient.phosphorus_mg_per_100g,
        iron_mg_per_100g=ingredient.iron_mg_per_100g,
        zinc_mg_per_100g=ingredient.zinc_mg_per_100g,
        vitamin_a_mcg_per_100g=ingredient.vitamin_a_mcg_per_100g,
        vitamin_d_mcg_per_100g=ingredient.vitamin_d_mcg_per_100g,
        vitamin_e_mg_per_100g=ingredient.vitamin_e_mg_per_100g,
    )
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    return db_ingredient


@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    """Get an ingredient by ID."""
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ingredient


@router.get("", response_model=list[IngredientResponse])
def list_ingredients(db: Session = Depends(get_db)):
    """List all ingredients."""
    return db.query(Ingredient).all()


@router.put("/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    ingredient_id: int,
    ingredient_update: IngredientUpdate,
    db: Session = Depends(get_db)
):
    """Update an ingredient."""
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    update_data = ingredient_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ingredient, field, value)

    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.delete("/{ingredient_id}", status_code=204)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    """Delete an ingredient."""
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    # Check if ingredient is used in any recipes
    if ingredient.recipe_ingredients:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete ingredient that is used in recipes. Remove from recipes first."
        )

    db.delete(ingredient)
    db.commit()
    return None
