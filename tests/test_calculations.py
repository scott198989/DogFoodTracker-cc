"""Tests for core calculation functions."""

import pytest
from app.core.calculations import (
    calculate_rer,
    calculate_mer,
    get_activity_factor,
    calculate_homemade_kcal,
    kcal_to_grams,
    grams_to_kcal,
    calculate_nutrient_amount,
    aggregate_nutrients,
    nutrient_per_1000kcal,
    check_aafco_compliance,
    ACTIVITY_FACTORS,
)


class TestRERCalculation:
    """Tests for Resting Energy Requirement calculation."""

    def test_rer_10kg_dog(self):
        """Test RER for a 10kg dog."""
        # RER = 70 * (10 ^ 0.75) = 70 * 5.623 = 393.62
        rer = calculate_rer(10)
        assert round(rer, 2) == 393.62

    def test_rer_20kg_dog(self):
        """Test RER for a 20kg dog."""
        # RER = 70 * (20 ^ 0.75) = 70 * 9.457 = 662.0
        rer = calculate_rer(20)
        assert round(rer, 1) == 662.0

    def test_rer_5kg_dog(self):
        """Test RER for a small 5kg dog."""
        # RER = 70 * (5 ^ 0.75) = 70 * 3.344 = 234.08
        rer = calculate_rer(5)
        assert round(rer, 2) == 234.08

    def test_rer_invalid_weight(self):
        """Test RER with invalid weight raises error."""
        with pytest.raises(ValueError):
            calculate_rer(0)
        with pytest.raises(ValueError):
            calculate_rer(-5)


class TestActivityFactors:
    """Tests for activity factor determination."""

    def test_neutered_adult(self):
        """Test factor for neutered adult dog."""
        factor = get_activity_factor(neutered=True, age_years=3)
        assert factor == ACTIVITY_FACTORS["neutered_adult"]
        assert factor == 1.6

    def test_intact_adult(self):
        """Test factor for intact adult dog."""
        factor = get_activity_factor(neutered=False, age_years=3)
        assert factor == ACTIVITY_FACTORS["intact_adult"]
        assert factor == 1.8

    def test_young_puppy(self):
        """Test factor for young puppy (under 4 months)."""
        factor = get_activity_factor(neutered=False, age_years=0.2)  # ~2.4 months
        assert factor == ACTIVITY_FACTORS["puppy_young"]
        assert factor == 3.0

    def test_older_puppy(self):
        """Test factor for older puppy (4-12 months)."""
        factor = get_activity_factor(neutered=False, age_years=0.6)  # ~7 months
        assert factor == ACTIVITY_FACTORS["puppy_older"]
        assert factor == 2.0

    def test_weight_loss(self):
        """Test factor for weight loss goal."""
        factor = get_activity_factor(
            neutered=True, age_years=5,
            target_weight_kg=20, current_weight_kg=25
        )
        assert factor == ACTIVITY_FACTORS["weight_loss"]
        assert factor == 1.1

    def test_weight_gain(self):
        """Test factor for weight gain goal."""
        factor = get_activity_factor(
            neutered=True, age_years=5,
            target_weight_kg=25, current_weight_kg=20
        )
        assert factor == ACTIVITY_FACTORS["weight_gain"]
        assert factor == 1.8


class TestMERCalculation:
    """Tests for Maintenance Energy Requirement calculation."""

    def test_mer_neutered_10kg_dog(self):
        """Test MER for a neutered 10kg dog."""
        # RER = 393.62, factor = 1.6
        # MER = 393.62 * 1.6 = 629.79
        mer = calculate_mer(10, 1.6)
        assert round(mer, 2) == 629.79

    def test_mer_puppy_5kg(self):
        """Test MER for a 5kg puppy."""
        # RER = 234.08, factor = 2.0
        # MER = 234.08 * 2.0 = 468.16
        mer = calculate_mer(5, 2.0)
        assert round(mer, 2) == 468.16


class TestCalorieConversions:
    """Tests for kcal to grams conversions."""

    def test_kcal_to_grams(self):
        """Test converting kcal to grams."""
        # For an ingredient with 200 kcal/100g, 100 kcal = 50g
        grams = kcal_to_grams(100, 200)
        assert grams == 50

    def test_grams_to_kcal(self):
        """Test converting grams to kcal."""
        # For an ingredient with 200 kcal/100g, 50g = 100 kcal
        kcal = grams_to_kcal(50, 200)
        assert kcal == 100

    def test_kcal_to_grams_invalid(self):
        """Test kcal_to_grams with invalid kcal_per_100g."""
        with pytest.raises(ValueError):
            kcal_to_grams(100, 0)


class TestHomemadeCalories:
    """Tests for homemade food calorie allocation."""

    def test_full_allocation(self):
        """Test when all calories go to homemade."""
        homemade = calculate_homemade_kcal(600, 0, 0)
        assert homemade == 600

    def test_with_kibble_and_treats(self):
        """Test with kibble and treats subtracted."""
        homemade = calculate_homemade_kcal(600, 200, 50)
        assert homemade == 350

    def test_over_allocation_returns_zero(self):
        """Test that negative values return 0."""
        homemade = calculate_homemade_kcal(600, 400, 300)
        assert homemade == 0


class TestNutrientAggregation:
    """Tests for nutrient aggregation."""

    def test_calculate_nutrient_amount(self):
        """Test nutrient calculation for given grams."""
        # 50g of ingredient with 20g protein per 100g = 10g protein
        amount = calculate_nutrient_amount(50, 20)
        assert amount == 10

    def test_aggregate_nutrients_single(self):
        """Test aggregation with single ingredient."""
        ingredients = [{
            "grams": 100,
            "kcal_per_100g": 150,
            "protein_g_per_100g": 25,
            "fat_g_per_100g": 5,
            "carbs_g_per_100g": 0,
            "calcium_mg_per_100g": 10,
            "phosphorus_mg_per_100g": 200,
            "iron_mg_per_100g": 1.5,
            "zinc_mg_per_100g": 2.0,
            "vitamin_a_mcg_per_100g": 50,
            "vitamin_d_mcg_per_100g": 0.5,
            "vitamin_e_mg_per_100g": 0.3,
        }]
        totals = aggregate_nutrients(ingredients)
        assert totals.kcal == 150
        assert totals.protein_g == 25
        assert totals.calcium_mg == 10

    def test_aggregate_nutrients_multiple(self):
        """Test aggregation with multiple ingredients."""
        ingredients = [
            {
                "grams": 100,
                "kcal_per_100g": 150,
                "protein_g_per_100g": 25,
                "fat_g_per_100g": 5,
                "carbs_g_per_100g": 0,
                "calcium_mg_per_100g": 10,
                "phosphorus_mg_per_100g": 200,
                "iron_mg_per_100g": 1.5,
                "zinc_mg_per_100g": 2.0,
                "vitamin_a_mcg_per_100g": 50,
                "vitamin_d_mcg_per_100g": 0.5,
                "vitamin_e_mg_per_100g": 0.3,
            },
            {
                "grams": 50,
                "kcal_per_100g": 100,
                "protein_g_per_100g": 10,
                "fat_g_per_100g": 2,
                "carbs_g_per_100g": 15,
                "calcium_mg_per_100g": 20,
                "phosphorus_mg_per_100g": 50,
                "iron_mg_per_100g": 0.5,
                "zinc_mg_per_100g": 0.5,
                "vitamin_a_mcg_per_100g": 100,
                "vitamin_d_mcg_per_100g": 0,
                "vitamin_e_mg_per_100g": 0.5,
            },
        ]
        totals = aggregate_nutrients(ingredients)
        # First: 150 kcal, Second: 50 kcal
        assert totals.kcal == 200
        # First: 25g, Second: 5g
        assert totals.protein_g == 30
        # First: 10mg, Second: 10mg
        assert totals.calcium_mg == 20


class TestAAFCOCompliance:
    """Tests for AAFCO compliance checking."""

    def test_nutrient_per_1000kcal(self):
        """Test conversion to per-1000kcal basis."""
        # 50mg in 500 kcal = 100mg per 1000 kcal
        per_1000 = nutrient_per_1000kcal(50, 500)
        assert per_1000 == 100

    def test_nutrient_per_1000kcal_zero_kcal(self):
        """Test conversion with zero calories returns 0."""
        per_1000 = nutrient_per_1000kcal(50, 0)
        assert per_1000 == 0

    def test_aafco_adequate(self):
        """Test AAFCO check for adequate nutrient."""
        result = check_aafco_compliance("calcium", 1500, 1250, 6250)
        assert result["status"] == "adequate"
        assert result["warning"] is None

    def test_aafco_deficient(self):
        """Test AAFCO check for deficient nutrient."""
        result = check_aafco_compliance("calcium", 1000, 1250, 6250)
        assert result["status"] == "deficient"
        assert "below minimum" in result["warning"]

    def test_aafco_excess(self):
        """Test AAFCO check for excess nutrient."""
        result = check_aafco_compliance("calcium", 7000, 1250, 6250)
        assert result["status"] == "excess"
        assert "above maximum" in result["warning"]

    def test_aafco_no_max(self):
        """Test AAFCO check when no maximum defined."""
        result = check_aafco_compliance("iron", 100, 10, None)
        assert result["status"] == "adequate"
        assert result["max_allowed"] is None
