"""Dog API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.calculations import calculate_rer, calculate_mer, get_activity_factor
from app.models.models import Dog
from app.schemas.schemas import DogCreate, DogResponse, DogWithCalculations

router = APIRouter(prefix="/dog", tags=["dogs"])


@router.post("", response_model=DogResponse, status_code=201)
def create_dog(dog: DogCreate, db: Session = Depends(get_db)):
    """Create a new dog profile."""
    db_dog = Dog(
        name=dog.name,
        age_years=dog.age_years,
        sex=dog.sex.value,
        neutered=dog.neutered,
        weight_kg=dog.weight_kg,
        target_weight_kg=dog.target_weight_kg,
        activity_level=dog.activity_level.value,
    )
    db.add(db_dog)
    db.commit()
    db.refresh(db_dog)
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

    return DogWithCalculations(
        id=dog.id,
        name=dog.name,
        age_years=dog.age_years,
        sex=dog.sex,
        neutered=dog.neutered,
        weight_kg=dog.weight_kg,
        target_weight_kg=dog.target_weight_kg,
        activity_level=dog.activity_level,
        rer=round(rer, 2),
        mer=round(mer, 2),
        activity_factor=factor,
    )


@router.get("", response_model=list[DogResponse])
def list_dogs(db: Session = Depends(get_db)):
    """List all dogs."""
    dogs = db.query(Dog).all()
    return dogs
