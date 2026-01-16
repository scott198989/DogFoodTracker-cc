from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Dog Meal Planner API"
    DATABASE_URL: str = "sqlite:///./dog_meal_planner.db"
    USDA_API_KEY: str = ""
    USDA_BASE_URL: str = "https://api.nal.usda.gov/fdc/v1"

    class Config:
        env_file = ".env"


settings = Settings()
