"""Weight and Feeding Log API endpoints."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.models import Dog, WeightLog, FeedingLog, Recipe
from app.schemas.schemas import (
    WeightLogCreate,
    WeightLogResponse,
    FeedingLogCreate,
    FeedingLogResponse,
    DailySummary,
)

router = APIRouter(prefix="/log", tags=["logs"])


# ==================== Weight Logs ====================

@router.post("/weight", response_model=WeightLogResponse, status_code=201)
def create_weight_log(log: WeightLogCreate, db: Session = Depends(get_db)):
    """Log a weight measurement for a dog."""
    dog = db.query(Dog).filter(Dog.id == log.dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    weight_log = WeightLog(
        dog_id=log.dog_id,
        weight_kg=log.weight_kg,
        notes=log.notes,
    )
    db.add(weight_log)

    # Also update the dog's current weight
    dog.weight_kg = log.weight_kg

    db.commit()
    db.refresh(weight_log)
    return weight_log


@router.get("/weight/dog/{dog_id}", response_model=list[WeightLogResponse])
def get_weight_logs_for_dog(
    dog_id: int,
    limit: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get weight history for a dog."""
    dog = db.query(Dog).filter(Dog.id == dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    logs = (
        db.query(WeightLog)
        .filter(WeightLog.dog_id == dog_id)
        .order_by(WeightLog.logged_at.desc())
        .limit(limit)
        .all()
    )
    return logs


@router.delete("/weight/{log_id}", status_code=204)
def delete_weight_log(log_id: int, db: Session = Depends(get_db)):
    """Delete a weight log entry."""
    log = db.query(WeightLog).filter(WeightLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Weight log not found")

    db.delete(log)
    db.commit()
    return None


# ==================== Feeding Logs ====================

@router.post("/feeding", response_model=FeedingLogResponse, status_code=201)
def create_feeding_log(log: FeedingLogCreate, db: Session = Depends(get_db)):
    """Log a feeding/meal for a dog."""
    dog = db.query(Dog).filter(Dog.id == log.dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    if log.recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == log.recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

    feeding_log = FeedingLog(
        dog_id=log.dog_id,
        recipe_id=log.recipe_id,
        meal_type=log.meal_type,
        kcal_fed=log.kcal_fed,
        notes=log.notes,
    )
    db.add(feeding_log)
    db.commit()
    db.refresh(feeding_log)

    return _feeding_log_to_response(feeding_log)


@router.get("/feeding/dog/{dog_id}", response_model=list[FeedingLogResponse])
def get_feeding_logs_for_dog(
    dog_id: int,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get feeding history for a dog."""
    dog = db.query(Dog).filter(Dog.id == dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    since = datetime.utcnow() - timedelta(days=days)
    logs = (
        db.query(FeedingLog)
        .filter(FeedingLog.dog_id == dog_id)
        .filter(FeedingLog.logged_at >= since)
        .order_by(FeedingLog.logged_at.desc())
        .all()
    )
    return [_feeding_log_to_response(log) for log in logs]


@router.get("/feeding/today/{dog_id}", response_model=list[FeedingLogResponse])
def get_todays_feeding_logs(dog_id: int, db: Session = Depends(get_db)):
    """Get today's feeding logs for a dog."""
    dog = db.query(Dog).filter(Dog.id == dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    logs = (
        db.query(FeedingLog)
        .filter(FeedingLog.dog_id == dog_id)
        .filter(FeedingLog.logged_at >= today_start)
        .order_by(FeedingLog.logged_at.desc())
        .all()
    )
    return [_feeding_log_to_response(log) for log in logs]


@router.delete("/feeding/{log_id}", status_code=204)
def delete_feeding_log(log_id: int, db: Session = Depends(get_db)):
    """Delete a feeding log entry."""
    log = db.query(FeedingLog).filter(FeedingLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Feeding log not found")

    db.delete(log)
    db.commit()
    return None


# ==================== Daily Summary ====================

@router.get("/summary/today/{dog_id}", response_model=DailySummary)
def get_daily_summary(dog_id: int, db: Session = Depends(get_db)):
    """Get today's feeding summary for a dog."""
    dog = db.query(Dog).filter(Dog.id == dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get today's total calories fed
    result = (
        db.query(func.sum(FeedingLog.kcal_fed), func.count(FeedingLog.id))
        .filter(FeedingLog.dog_id == dog_id)
        .filter(FeedingLog.logged_at >= today_start)
        .first()
    )

    total_kcal_fed = result[0] or 0
    meals_logged = result[1] or 0

    # Calculate target kcal (use custom target or calculated MER)
    from app.core.calculations import calculate_rer, calculate_mer, get_activity_factor

    if dog.target_daily_kcal:
        target_kcal = dog.target_daily_kcal
    else:
        factor = get_activity_factor(
            neutered=dog.neutered,
            age_years=dog.age_years,
            target_weight_kg=dog.target_weight_kg,
            current_weight_kg=dog.weight_kg
        )
        target_kcal = calculate_mer(dog.weight_kg, factor)

    remaining_kcal = max(0, target_kcal - total_kcal_fed)

    # Consider "on track" if within 10% of target
    on_track = total_kcal_fed <= target_kcal * 1.1

    return DailySummary(
        date=today_start.strftime("%Y-%m-%d"),
        dog_id=dog.id,
        dog_name=dog.name,
        target_kcal=round(target_kcal, 2),
        total_kcal_fed=round(total_kcal_fed, 2),
        remaining_kcal=round(remaining_kcal, 2),
        meals_logged=meals_logged,
        on_track=on_track,
    )


def _feeding_log_to_response(log: FeedingLog) -> FeedingLogResponse:
    """Convert FeedingLog model to response schema."""
    return FeedingLogResponse(
        id=log.id,
        dog_id=log.dog_id,
        recipe_id=log.recipe_id,
        recipe_name=log.recipe.name if log.recipe else None,
        meal_type=log.meal_type,
        kcal_fed=log.kcal_fed,
        notes=log.notes,
        logged_at=log.logged_at,
    )
