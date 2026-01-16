"""
Dog Meal Planner API - Main Application

A production-quality MVP backend for calculating precise dog meals
using real nutrition data from USDA FoodData Central.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.api import dogs, ingredients, recipes, plans

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Dog Meal Planner API

    Calculate precise dog meals using real nutrition data.

    ### Features
    - Accurate calorie calculation (RER/MER)
    - Ingredient-level nutrition from USDA FoodData Central
    - Recipe builder with gram-based portions
    - AAFCO compliance checking
    - Nutrient aggregation and deficiency warnings

    ### Core Endpoints
    - `/dog` - Manage dog profiles
    - `/ingredient` - Search and manage ingredients
    - `/recipe` - Build recipes with ingredients
    - `/plan/compute` - Calculate complete feeding plans
    """,
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dogs.router)
app.include_router(ingredients.router)
app.include_router(recipes.router)
app.include_router(plans.router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "dogs": "/dog",
            "ingredients": "/ingredient",
            "recipes": "/recipe",
            "plans": "/plan",
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
