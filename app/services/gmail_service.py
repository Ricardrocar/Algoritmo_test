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
        
        if not os.path.exists(token_path):
            return False
        
        if os.path.isdir(token_path):
            print(f"ADVERTENCIA: {token_path} es un directorio, eliminándolo...")
            try:
                shutil.rmtree(token_path)
                print(f"Directorio {token_path} eliminado correctamente")
                return False
            except Exception as e:
                print(f"Error al eliminar directorio {token_path}: {e}")
                return False
        
        if not os.path.isfile(token_path):
            print(f"ADVERTENCIA: {token_path} no es un archivo válido")
            return False
        
        try:
            self.creds = Credentials.from_authorized_user_file(
                token_path,
                self.settings.GMAIL_SCOPES_LIST
            )
            return True
        except (ValueError, json.JSONDecodeError, Exception) as e:
            print(f"Error al cargar credenciales: {e}")
            return False
    
    def save_credentials(self):
        if not self.creds:
            return
        
        token_path = self.settings.GMAIL_TOKEN_FILE
        
        if os.path.exists(token_path):
            if os.path.isdir(token_path):
                print(f"ADVERTENCIA: {token_path} es un directorio, eliminándolo...")
                try:
                    shutil.rmtree(token_path)
                    print(f"Directorio {token_path} eliminado correctamente")
                except Exception as e:
                    print(f"Error al eliminar directorio {token_path}: {e}")
                    raise
            elif os.path.isfile(token_path):
                try:
                    os.remove(token_path)
                except Exception as e:
                    print(f"Error al eliminar archivo {token_path}: {e}")
        
        token_dir = os.path.dirname(token_path)
        if token_dir and not os.path.exists(token_dir):
            os.makedirs(token_dir, exist_ok=True)
        
        try:
            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())
            print(f"Token guardado correctamente en {token_path}")
        except Exception as e:
            print(f"Error al escribir token en {token_path}: {e}")
            raise
    
    def refresh_credentials(self) -> bool:
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
        except Exception as e:
            print(f"Error al intercambiar código por token: {e}")
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
    
    def build_service(self):
        if not self.is_authenticated():
            raise ValueError("No autenticado. Por favor autentícate primero.")
        
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            return self.service
        except Exception as e:
            print(f"Error al construir servicio: {e}")
            raise
    
    def test_connection(self) -> dict:
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
    
    def setup_watch(self, topic_name: str, label_ids: list = None) -> dict:
        try:
            if not self.service:
                self.build_service()
            
            if label_ids is None:
                label_ids = ['INBOX']
            
            watch_request = {
                'labelIds': label_ids,
                'topicName': topic_name
            }
            
            result = self.service.users().watch(
                userId='me',
                body=watch_request
            ).execute()
            
            return {
                "status": "success",
                "history_id": result.get('historyId'),
                "expiration": result.get('expiration')
            }
        except HttpError as error:
            return {
                "status": "error",
                "message": f"Error al configurar watch: {error}"
            }
        except Exception as error:
            return {
                "status": "error",
                "message": f"Error inesperado: {error}"
            }
    
    def stop_watch(self) -> dict:
        try:
            if not self.service:
                self.build_service()
            
            self.service.users().stop(userId='me').execute()
            return {"status": "success", "message": "Watch detenido correctamente"}
        except HttpError as error:
            return {
                "status": "error",
                "message": f"Error al detener watch: {error}"
            }
        except Exception as error:
            return {
                "status": "error",
                "message": f"Error inesperado: {error}"
            }
    
_gmail_service_instance: Optional[GmailService] = None

def get_gmail_service() -> GmailService:
    global _gmail_service_instance
    if _gmail_service_instance is None:
        _gmail_service_instance = GmailService()
    return _gmail_service_instance
