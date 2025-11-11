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
    GMAIL_PUBSUB_PROJECT_ID: str = ""
    GMAIL_PUBSUB_TOPIC_ID: str = ""
    GMAIL_PUBSUB_SUBSCRIPTION_ID: str = ""
    GMAIL_WATCH_LABEL_IDS: str = "INBOX"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def GMAIL_SCOPES_LIST(self) -> list:
        """Convertir GMAIL_SCOPES de string a lista."""
        return [scope.strip() for scope in self.GMAIL_SCOPES.split(",")]
    
    @property
    def GMAIL_WATCH_LABEL_IDS_LIST(self) -> list:
        if not self.GMAIL_WATCH_LABEL_IDS:
            return []
        return [label.strip() for label in self.GMAIL_WATCH_LABEL_IDS.split(",") if label.strip()]
    
    @property
    def GMAIL_PUBSUB_TOPIC_PATH(self) -> str:
        if not self.GMAIL_PUBSUB_PROJECT_ID or not self.GMAIL_PUBSUB_TOPIC_ID:
            return ""
        return f"projects/{self.GMAIL_PUBSUB_PROJECT_ID}/topics/{self.GMAIL_PUBSUB_TOPIC_ID}"
    
    @property
    def GMAIL_PUBSUB_SUBSCRIPTION_PATH(self) -> str:
        if not self.GMAIL_PUBSUB_PROJECT_ID or not self.GMAIL_PUBSUB_SUBSCRIPTION_ID:
            return ""
        return f"projects/{self.GMAIL_PUBSUB_PROJECT_ID}/subscriptions/{self.GMAIL_PUBSUB_SUBSCRIPTION_ID}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

