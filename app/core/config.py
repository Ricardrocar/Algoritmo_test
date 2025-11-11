from functools import lru_cache
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "Gmail Analyzer API"
    APP_VERSION: str = "0.1.0"
@lru_cache()
def get_settings() -> Settings:
    return Settings()

