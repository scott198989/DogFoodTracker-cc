-- Fresh Pup Database Schema for Supabase
-- Run this in Supabase SQL Editor to set up your database

-- Enable UUID extension (should already be enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

CREATE TYPE sex_type AS ENUM ('male', 'female');
CREATE TYPE activity_level_type AS ENUM ('low', 'moderate', 'high');
CREATE TYPE life_stage_type AS ENUM ('puppy', 'adult', 'senior');
CREATE TYPE source_type AS ENUM ('USDA', 'BRAND', 'USER');
CREATE TYPE ingredient_type AS ENUM ('food', 'oil', 'supplement', 'treat');
CREATE TYPE food_category_type AS ENUM ('protein', 'carbs', 'vegetables', 'fruits', 'fats', 'seeds', 'supplements', 'other');

-- ============================================================================
-- TABLES
-- ============================================================================

-- Dogs table
CREATE TABLE dogs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    breed VARCHAR,
    age_years FLOAT NOT NULL,
    sex sex_type NOT NULL,
    neutered BOOLEAN NOT NULL,
    weight_kg FLOAT NOT NULL,
    target_weight_kg FLOAT,
    target_daily_kcal FLOAT,
    activity_level activity_level_type DEFAULT 'moderate',
    life_stage life_stage_type DEFAULT 'adult',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ingredients table (shared USDA + user-specific)
CREATE TABLE ingredients (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    source_type source_type NOT NULL,
    source_id VARCHAR,
    ingredient_type ingredient_type DEFAULT 'food',
    category food_category_type DEFAULT 'other',
    kcal_per_100g FLOAT NOT NULL,
    protein_g_per_100g FLOAT DEFAULT 0,
    fat_g_per_100g FLOAT DEFAULT 0,
    carbs_g_per_100g FLOAT DEFAULT 0,
    calcium_mg_per_100g FLOAT DEFAULT 0,
    phosphorus_mg_per_100g FLOAT DEFAULT 0,
    iron_mg_per_100g FLOAT DEFAULT 0,
    zinc_mg_per_100g FLOAT DEFAULT 0,
    vitamin_a_mcg_per_100g FLOAT DEFAULT 0,
    vitamin_d_mcg_per_100g FLOAT DEFAULT 0,
    vitamin_e_mg_per_100g FLOAT DEFAULT 0,
    kcal_per_ml FLOAT,
    serving_size_ml FLOAT,
    kcal_per_unit FLOAT,
    units_per_day FLOAT
);

-- Recipes table
CREATE TABLE recipes (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    meals_per_day INTEGER DEFAULT 2
);

-- Recipe ingredients junction table
CREATE TABLE recipe_ingredients (
    id SERIAL PRIMARY KEY,
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE NOT NULL,
    ingredient_id INTEGER REFERENCES ingredients(id) ON DELETE CASCADE NOT NULL,
    percentage FLOAT NOT NULL
);

-- Feeding plans table
CREATE TABLE feeding_plans (
    id SERIAL PRIMARY KEY,
    dog_id INTEGER REFERENCES dogs(id) ON DELETE CASCADE NOT NULL,
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE NOT NULL,
    kibble_kcal FLOAT DEFAULT 0,
    treats_kcal FLOAT DEFAULT 0,
    homemade_kcal FLOAT DEFAULT 0,
    target_kcal FLOAT NOT NULL
);

-- AAFCO requirements (shared, no user_id)
CREATE TABLE aafco_requirements (
    id SERIAL PRIMARY KEY,
    nutrient VARCHAR NOT NULL UNIQUE,
    min_per_1000kcal FLOAT NOT NULL,
    max_per_1000kcal FLOAT
);

-- Weight logs
CREATE TABLE weight_logs (
    id SERIAL PRIMARY KEY,
    dog_id INTEGER REFERENCES dogs(id) ON DELETE CASCADE NOT NULL,
    weight_kg FLOAT NOT NULL,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes VARCHAR
);

-- Feeding logs
CREATE TABLE feeding_logs (
    id SERIAL PRIMARY KEY,
    dog_id INTEGER REFERENCES dogs(id) ON DELETE CASCADE NOT NULL,
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
    meal_type VARCHAR,
    kcal_fed FLOAT NOT NULL,
    notes VARCHAR,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_dogs_user_id ON dogs(user_id);
CREATE INDEX idx_ingredients_user_id ON ingredients(user_id);
CREATE INDEX idx_ingredients_name ON ingredients(name);
CREATE INDEX idx_recipes_user_id ON recipes(user_id);
CREATE INDEX idx_weight_logs_dog_id ON weight_logs(dog_id);
CREATE INDEX idx_feeding_logs_dog_id ON feeding_logs(dog_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all user-specific tables
ALTER TABLE dogs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE feeding_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE weight_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE feeding_logs ENABLE ROW LEVEL SECURITY;

-- Dogs: Users can only see/modify their own dogs
CREATE POLICY "Users can view own dogs" ON dogs
    FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can insert own dogs" ON dogs
    FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can update own dogs" ON dogs
    FOR UPDATE USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can delete own dogs" ON dogs
    FOR DELETE USING (auth.uid() = user_id OR user_id IS NULL);

-- Ingredients: Users see shared (NULL user_id) + their own
CREATE POLICY "Users can view shared and own ingredients" ON ingredients
    FOR SELECT USING (user_id IS NULL OR auth.uid() = user_id);

CREATE POLICY "Users can insert own ingredients" ON ingredients
    FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can update own ingredients" ON ingredients
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own ingredients" ON ingredients
    FOR DELETE USING (auth.uid() = user_id);

-- Recipes: Users can only see/modify their own recipes
CREATE POLICY "Users can view own recipes" ON recipes
    FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can insert own recipes" ON recipes
    FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can update own recipes" ON recipes
    FOR UPDATE USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can delete own recipes" ON recipes
    FOR DELETE USING (auth.uid() = user_id OR user_id IS NULL);

-- Recipe ingredients: Based on recipe ownership
CREATE POLICY "Users can view own recipe ingredients" ON recipe_ingredients
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM recipes WHERE recipes.id = recipe_ingredients.recipe_id
                AND (recipes.user_id = auth.uid() OR recipes.user_id IS NULL))
    );

CREATE POLICY "Users can insert own recipe ingredients" ON recipe_ingredients
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM recipes WHERE recipes.id = recipe_ingredients.recipe_id
                AND (recipes.user_id = auth.uid() OR recipes.user_id IS NULL))
    );

CREATE POLICY "Users can update own recipe ingredients" ON recipe_ingredients
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM recipes WHERE recipes.id = recipe_ingredients.recipe_id
                AND (recipes.user_id = auth.uid() OR recipes.user_id IS NULL))
    );

CREATE POLICY "Users can delete own recipe ingredients" ON recipe_ingredients
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM recipes WHERE recipes.id = recipe_ingredients.recipe_id
                AND (recipes.user_id = auth.uid() OR recipes.user_id IS NULL))
    );

-- Feeding plans: Based on dog ownership
CREATE POLICY "Users can view own feeding plans" ON feeding_plans
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = feeding_plans.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can insert own feeding plans" ON feeding_plans
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = feeding_plans.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can update own feeding plans" ON feeding_plans
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = feeding_plans.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can delete own feeding plans" ON feeding_plans
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = feeding_plans.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

-- Weight logs: Based on dog ownership
CREATE POLICY "Users can view own weight logs" ON weight_logs
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = weight_logs.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can insert own weight logs" ON weight_logs
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = weight_logs.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can update own weight logs" ON weight_logs
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = weight_logs.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can delete own weight logs" ON weight_logs
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = weight_logs.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

-- Feeding logs: Based on dog ownership
CREATE POLICY "Users can view own feeding logs" ON feeding_logs
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = feeding_logs.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can insert own feeding logs" ON feeding_logs
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = feeding_logs.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can update own feeding logs" ON feeding_logs
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = feeding_logs.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

CREATE POLICY "Users can delete own feeding logs" ON feeding_logs
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM dogs WHERE dogs.id = feeding_logs.dog_id
                AND (dogs.user_id = auth.uid() OR dogs.user_id IS NULL))
    );

-- ============================================================================
-- SEED DATA: AAFCO Requirements
-- ============================================================================

INSERT INTO aafco_requirements (nutrient, min_per_1000kcal, max_per_1000kcal) VALUES
    ('protein', 45.0, NULL),
    ('fat', 13.75, NULL),
    ('calcium', 1.25, 6.25),
    ('phosphorus', 1.0, 4.0),
    ('iron', 10.0, NULL),
    ('zinc', 20.0, NULL),
    ('vitamin_a', 1250.0, 62500.0),
    ('vitamin_d', 3.125, 18.75),
    ('vitamin_e', 12.5, NULL);

-- ============================================================================
-- DONE!
-- ============================================================================
