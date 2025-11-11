from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    APP_NAME: str = "Gmail Analyzer API"
    APP_VERSION: str = "0.1.0"
    
    # Gmail API Configuration
    GMAIL_CREDENTIALS_FILE: str = "credentials.json"
    GMAIL_TOKEN_FILE: str = "token.json"
    GMAIL_SCOPES: list = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify"
    ]
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/emails/oauth2callback"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

