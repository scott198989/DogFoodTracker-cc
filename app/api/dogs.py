"""Dog API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.calculations import calculate_rer, calculate_mer, get_activity_factor
from app.models.models import Dog, WeightLog
from app.schemas.schemas import DogCreate, DogUpdate, DogResponse, DogWithCalculations

router = APIRouter(prefix="/dog", tags=["dogs"])


def get_weight_status(current_kg: float, target_kg: float | None) -> str:
    """Determine weight status relative to target."""
    if target_kg is None:
        return "no_target"
    diff = current_kg - target_kg
    if abs(diff) < 0.5:  # Within 0.5kg is considered at target
        return "at_target"
    elif diff > 0:
        return "needs_loss"
    else:
        return "needs_gain"


@router.post("", response_model=DogResponse, status_code=201)
def create_dog(dog: DogCreate, db: Session = Depends(get_db)):
    """Create a new dog profile."""
    db_dog = Dog(
        name=dog.name,
        breed=dog.breed,
        age_years=dog.age_years,
        sex=dog.sex.value,
        neutered=dog.neutered,
        weight_kg=dog.weight_kg,
        target_weight_kg=dog.target_weight_kg,
        target_daily_kcal=dog.target_daily_kcal,
        activity_level=dog.activity_level.value,
        life_stage=dog.life_stage.value,
        notes=dog.notes,
    )
    db.add(db_dog)
    db.commit()
    db.refresh(db_dog)

    # Create initial weight log entry
    weight_log = WeightLog(
        dog_id=db_dog.id,
        weight_kg=dog.weight_kg,
        notes="Initial weight"
    )
    db.add(weight_log)
    db.commit()

    return db_dog


@router.get("/{dog_id}", response_model=DogWithCalculations)
def get_dog(dog_id: int, db: Session = Depends(get_db)):
    """Get a dog profile with calculated RER and MER."""
    dog = db.query(Dog).filter(Dog.id == dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    # Calculate energy requirements
    rer = calculate_rer(dog.weight_kg)
    factor = get_activity_factor(
        neutered=dog.neutered,
        age_years=dog.age_years,
        target_weight_kg=dog.target_weight_kg,
        current_weight_kg=dog.weight_kg
    )
    mer = calculate_mer(dog.weight_kg, factor)

    # Use target_daily_kcal if set, otherwise use calculated MER
    effective_daily_kcal = dog.target_daily_kcal if dog.target_daily_kcal else mer

    # Determine weight status
    weight_status = get_weight_status(dog.weight_kg, dog.target_weight_kg)

    return DogWithCalculations(
        id=dog.id,
        name=dog.name,
        breed=dog.breed,
        age_years=dog.age_years,
        sex=dog.sex,
        neutered=dog.neutered,
        weight_kg=dog.weight_kg,
        target_weight_kg=dog.target_weight_kg,
        target_daily_kcal=dog.target_daily_kcal,
        activity_level=dog.activity_level,
        life_stage=dog.life_stage,
        notes=dog.notes,
        rer=round(rer, 2),
        mer=round(mer, 2),
        effective_daily_kcal=round(effective_daily_kcal, 2),
        activity_factor=factor,
        weight_status=weight_status,
    )


@router.get("", response_model=list[DogResponse])
def list_dogs(db: Session = Depends(get_db)):
    """List all dogs."""
    dogs = db.query(Dog).all()
    return dogs


@router.put("/{dog_id}", response_model=DogResponse)
def update_dog(dog_id: int, dog_update: DogUpdate, db: Session = Depends(get_db)):
    """Update a dog profile."""
    dog = db.query(Dog).filter(Dog.id == dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    old_weight = dog.weight_kg
    update_data = dog_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field in ("sex", "activity_level", "life_stage") and value is not None:
            setattr(dog, field, value.value)
        elif field in ("target_weight_kg", "target_daily_kcal") and value == 0:
            # Allow clearing target values by setting to 0
            setattr(dog, field, None)
        else:
            setattr(dog, field, value)

    # If weight changed, create a weight log entry
    if "weight_kg" in update_data and update_data["weight_kg"] != old_weight:
        weight_log = WeightLog(
            dog_id=dog.id,
            weight_kg=update_data["weight_kg"],
            notes="Weight updated"
        )
        db.add(weight_log)

    db.commit()
    db.refresh(dog)
    return dog


@router.delete("/{dog_id}", status_code=204)
def delete_dog(dog_id: int, db: Session = Depends(get_db)):
    """Delete a dog profile."""
    dog = db.query(Dog).filter(Dog.id == dog_id).first()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    db.delete(dog)
    db.commit()
    return None
