import os
import json
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import get_settings

class GmailService:
    """Servicio para interactuar con la API de Gmail usando OAuth2."""
    def __init__(self):
        self.settings = get_settings()
        self.creds: Optional[Credentials] = None
        self.service = None
    
    def load_credentials(self) -> bool:
        """Cargar credenciales desde el archivo de token si existe."""
        if not os.path.exists(self.settings.GMAIL_TOKEN_FILE):
            return False
        
        try:
            self.creds = Credentials.from_authorized_user_file(
                self.settings.GMAIL_TOKEN_FILE,
                self.settings.GMAIL_SCOPES_LIST
            )
            return True
        except (ValueError, json.JSONDecodeError, Exception) as e:
            print(f"Error al cargar credenciales: {e}")
            return False
    
    def save_credentials(self):
        """Guardar credenciales en el archivo de token."""
        if not self.creds:
            return
        
        with open(self.settings.GMAIL_TOKEN_FILE, 'w') as token:
            token.write(self.creds.to_json())
    
    def refresh_credentials(self) -> bool:
        """Refrescar credenciales expiradas."""
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self.save_credentials()
                return True
            except Exception as e:
                print(f"Error al refrescar credenciales: {e}")
                return False
        return False
    
    def is_authenticated(self) -> bool:
        """Verificar si el usuario está autenticado y las credenciales son válidas."""
        if not self.load_credentials():
            return False
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                return self.refresh_credentials()
            return False
        return True
    
    def get_authorization_url(self) -> tuple[str, Flow]:
        """Generar URL de autorización para el flujo OAuth2."""
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
        """Intercambiar código de autorización por credenciales."""
        try:
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            self.save_credentials()
            return True
        except Exception as e:
            print(f"Error al intercambiar código por token: {e}")
            return False
    
    def build_service(self):
        """Construir servicio de Gmail API."""
        if not self.is_authenticated():
            raise ValueError("No autenticado. Por favor autentícate primero.")
        
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            return self.service
        except Exception as e:
            print(f"Error al construir servicio: {e}")
            raise
    
    def test_connection(self) -> dict:
        """Probar conexión con Gmail API obteniendo el perfil del usuario."""
        try:
            if not self.service:
                self.build_service()
            
            profile = self.service.users().getProfile(userId='me').execute()
            return {
                "status": "success",
                "email": profile.get('emailAddress'),
                "total_messages": profile.get('messagesTotal'),
                "total_threads": profile.get('threadsTotal')
            }
        except HttpError as error:
            return {
                "status": "error",
                "message": f"Error de Gmail API: {error}"
            }
        except Exception as error:
            return {
                "status": "error",
                "message": f"Error inesperado: {error}"
            }
    
    def get_messages(self, max_results: int = 10, query: str = "") -> list:
        """Obtener mensajes de Gmail."""
        try:
            if not self.service:
                self.build_service()
            
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            return messages
        except HttpError as error:
            print(f"Error al obtener mensajes: {error}")
            return []
    
_gmail_service_instance: Optional[GmailService] = None

def get_gmail_service() -> GmailService:
    """Obtener o crear instancia del servicio de Gmail."""
    global _gmail_service_instance
    if _gmail_service_instance is None:
        _gmail_service_instance = GmailService()
    return _gmail_service_instance
