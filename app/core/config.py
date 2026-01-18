import os
from pydantic_settings import BaseSettings


def get_default_database_url() -> str:
    """Get default database URL based on environment."""
    # Check for Supabase/Postgres URL first
    if os.environ.get("DATABASE_URL"):
        return os.environ.get("DATABASE_URL")
    # Check if we're in a serverless environment (Vercel, AWS Lambda, etc.)
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        # Use /tmp for SQLite in serverless (ephemeral but writable)
        return "sqlite:////tmp/dog_meal_planner.db"
    return "sqlite:///./dog_meal_planner.db"


class Settings(BaseSettings):
    APP_NAME: str = "Dog Meal Planner API"
    DATABASE_URL: str = get_default_database_url()
    USDA_API_KEY: str = ""
    USDA_BASE_URL: str = "https://api.nal.usda.gov/fdc/v1"

    # Supabase settings
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""  # For server-side operations
    SUPABASE_JWT_SECRET: str = ""   # For verifying JWTs

    class Config:
        env_file = ".env"


settings = Settings()
