import os
import json
import shutil
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import get_settings

class GmailService:
    def __init__(self):
        self.settings = get_settings()
        self.creds: Optional[Credentials] = None
        self.service = None
    
    def load_credentials(self) -> bool:
        token_path = self.settings.GMAIL_TOKEN_FILE
        
        if not os.path.exists(token_path) or not os.path.isfile(token_path):
            if os.path.isdir(token_path):
                try:
                    shutil.rmtree(token_path)
                except Exception:
                    pass
            return False
        
        try:
            self.creds = Credentials.from_authorized_user_file(
                token_path,
                self.settings.GMAIL_SCOPES_LIST
            )
            return True
        except Exception:
            return False
    
    def save_credentials(self):
        if not self.creds:
            return
        
        token_path = self.settings.GMAIL_TOKEN_FILE
        
        try:
            if os.path.exists(token_path):
                if os.path.isdir(token_path):
                    shutil.rmtree(token_path)
                else:
                    os.remove(token_path)
        except Exception:
            pass
        
        token_dir = os.path.dirname(token_path)
        if token_dir:
            os.makedirs(token_dir, exist_ok=True)
        
        with open(token_path, 'w') as token:
            token.write(self.creds.to_json())
    
    def refresh_credentials(self) -> bool:
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self.save_credentials()
                return True
            except Exception:
                return False
        return False
    
    def is_authenticated(self) -> bool:
        if not self.load_credentials():
            return False
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                return self.refresh_credentials()
            return False
        return True
    
    def get_authorization_url(self) -> tuple[str, Flow]:
        if not os.path.exists(self.settings.GMAIL_CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"Archivo de credenciales no encontrado: {self.settings.GMAIL_CREDENTIALS_FILE}. "
                "Por favor descárgalo desde Google Cloud Console."
            )
        
        flow = Flow.from_client_secrets_file(
            self.settings.GMAIL_CREDENTIALS_FILE,
            scopes=self.settings.GMAIL_SCOPES_LIST,
            redirect_uri=self.settings.GMAIL_REDIRECT_URI
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url, flow
    
    def authenticate_with_code(self, code: str, flow: Flow) -> bool:
        try:
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            self.save_credentials()
            return True
        except Exception:
            return False
    
    def authenticate_with_installed_app_flow(self) -> bool:
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        if not os.path.exists(self.settings.GMAIL_CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"Archivo de credenciales no encontrado: {self.settings.GMAIL_CREDENTIALS_FILE}. "
                "Por favor descárgalo desde Google Cloud Console."
            )
        
        if self.is_authenticated():
            return True
        
        flow = InstalledAppFlow.from_client_secrets_file(
            self.settings.GMAIL_CREDENTIALS_FILE,
            self.settings.GMAIL_SCOPES_LIST
        )
        self.creds = flow.run_local_server(port=0)
        self.save_credentials()
        return True
    
    def _ensure_service(self):
        if not self.service:
            if not self.is_authenticated():
                raise ValueError("No autenticado. Por favor autentícate primero.")
            self.service = build('gmail', 'v1', credentials=self.creds)
    
    def build_service(self):
        self._ensure_service()
        return self.service
    
    def test_connection(self) -> dict:
        try:
            self._ensure_service()
            profile = self.service.users().getProfile(userId='me').execute()
            return {
                "status": "success",
                "email": profile.get('emailAddress'),
                "total_messages": profile.get('messagesTotal'),
                "total_threads": profile.get('threadsTotal')
            }
        except Exception as error:
            return {"status": "error", "message": str(error)}
    
    def get_messages(self, max_results: int = 10, query: str = "") -> list:
        try:
            self._ensure_service()
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            return results.get('messages', [])
        except Exception:
            return []
    
    def get_message_json(self, message_id: str) -> dict:
        self._ensure_service()
        return self.service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
    
_gmail_service_instance: Optional[GmailService] = None

def get_gmail_service() -> GmailService:
    global _gmail_service_instance
    if _gmail_service_instance is None:
        _gmail_service_instance = GmailService()
    return _gmail_service_instance
