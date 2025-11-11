"""
Script para autenticarse con Gmail API usando InstalledAppFlow.
Ejecutar: python auth_gmail.py
"""
import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Obtener la ruta del directorio donde está este script (raíz del proyecto)
SCRIPT_DIR = Path(__file__).parent.absolute()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]
CREDENTIALS_FILE = str(SCRIPT_DIR / 'credentials.json')
TOKEN_FILE = str(SCRIPT_DIR / 'token.json')

def is_token_valid(token_file: str) -> bool:
    """Verificar si el token.json existe y es válido."""
    if not os.path.exists(token_file):
        return False
    
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        if not all(key in token_data for key in ['token', 'refresh_token', 'client_id', 'client_secret']):
            return False
        
        creds = Credentials.from_authorized_user_info(token_data)
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, 'w') as f:
                f.write(creds.to_json())
            return True
        return creds.valid
        
    except (json.JSONDecodeError, ValueError, Exception) as e:
        print(f"Error al verificar token: {e}")
        return False

def authenticate():
    """Autenticarse con Gmail API usando InstalledAppFlow."""
    if is_token_valid(TOKEN_FILE):
        print("Token valido encontrado. No es necesario autenticarse nuevamente.")
        return True
    if not os.path.exists(CREDENTIALS_FILE):
        return False
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES
        )
        creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"Autenticacion exitosa!")
        try:
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
        except Exception as e:
            print(f"⚠️  Token guardado pero error al verificar conexión: {e}")
        return True
        
    except Exception as e:
        print(f"Error durante la autenticacion: {e}")
        return False


if __name__ == '__main__':
    success = authenticate()
    
    if success:
        print("Proceso completado. Ahora puedes usar la API.")
    else:
        print("La autenticacion fallo. Por favor revisa los errores arriba.")
        exit(1)

