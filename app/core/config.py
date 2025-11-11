from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "Gmail Analyzer API"
    APP_VERSION: str = "0.1.0"
    
    # Gmail API Configuration
    GMAIL_CREDENTIALS_FILE: str = "credentials.json"
    GMAIL_TOKEN_FILE: str = "token.json"
    GMAIL_SCOPES: str = "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.modify"
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/emails/oauth2callback"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def GMAIL_SCOPES_LIST(self) -> list:
        """Convertir GMAIL_SCOPES de string a lista."""
        return [scope.strip() for scope in self.GMAIL_SCOPES.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

