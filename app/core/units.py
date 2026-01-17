"""Weight unit conversion utilities."""

from enum import Enum


class WeightUnit(str, Enum):
    KG = "kg"
    LBS = "lbs"


# Conversion constants
KG_TO_LBS = 2.20462
LBS_TO_KG = 0.453592


def kg_to_lbs(kg: float) -> float:
    """Convert kilograms to pounds."""
    return round(kg * KG_TO_LBS, 2)


def lbs_to_kg(lbs: float) -> float:
    """Convert pounds to kilograms."""
    return round(lbs * LBS_TO_KG, 2)


def convert_weight(value: float, from_unit: WeightUnit, to_unit: WeightUnit) -> float:
    """Convert weight between units."""
    if from_unit == to_unit:
        return value
    if from_unit == WeightUnit.KG and to_unit == WeightUnit.LBS:
        return kg_to_lbs(value)
    if from_unit == WeightUnit.LBS and to_unit == WeightUnit.KG:
        return lbs_to_kg(value)
    return value


def format_weight(value: float, unit: WeightUnit) -> str:
    """Format weight with unit suffix."""
    return f"{value:.1f} {unit.value}"
