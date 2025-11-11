from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from app.services.gmail_service import get_gmail_service
from app.services.extraction_service import get_extraction_service


router = APIRouter(prefix="/emails", tags=["emails"])

_oauth_flows = {}


@router.get("/auth/status")
def auth_status():
    """Verificar estado de autenticación."""
    gmail_service = get_gmail_service()
    is_auth = gmail_service.is_authenticated()
    return {
        "authenticated": is_auth,
        "message": "Usuario autenticado" if is_auth else "Usuario necesita autenticarse"
    }

@router.get("/auth/login")
def login():
    """Iniciar flujo de login OAuth2."""
    try:
        gmail_service = get_gmail_service()
        auth_url, flow = gmail_service.get_authorization_url()
        flow_key = "current_flow"
        _oauth_flows[flow_key] = flow
        return {
            "auth_url": auth_url,
            "message": "Visita la auth_url para autorizar la aplicación"
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al iniciar login: {str(e)}")

@router.get("/oauth2callback")
async def oauth2_callback(request: Request):
    """Manejar callback OAuth2 de Google."""
    try:
        code = request.query_params.get('code')
        error = request.query_params.get('error')
        
        if error:
            raise HTTPException(status_code=400, detail=f"Error de autorización: {error}")
        
        if not code:
            raise HTTPException(status_code=400, detail="No se recibió código de autorización")
        
        flow_key = "current_flow"
        flow = _oauth_flows.get(flow_key)
        
        if not flow:
            gmail_service = get_gmail_service()
            try:
                from google_auth_oauthlib.flow import Flow
                from app.core.config import get_settings
                settings = get_settings()
                
                flow = Flow.from_client_secrets_file(
                    settings.GMAIL_CREDENTIALS_FILE,
                    scopes=settings.GMAIL_SCOPES,
                    redirect_uri=settings.GMAIL_REDIRECT_URI
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"No se pudo recrear el flujo OAuth. Por favor inicia login nuevamente. Error: {str(e)}"
                )
        
        gmail_service = get_gmail_service()
        success = gmail_service.authenticate_with_code(code, flow)
        _oauth_flows.pop(flow_key, None)
        
        if success:
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "¡Autenticación exitosa! Ahora puedes usar la API."
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Falló el intercambio de código de autorización")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en callback: {str(e)}")


@router.get("/ping")
def ping():
    """Probar conexión con Gmail API."""
    try:
        gmail_service = get_gmail_service()
        
        if not gmail_service.is_authenticated():
            raise HTTPException(
                status_code=401,
                detail="No autenticado. Por favor inicia sesión primero en /emails/auth/login"
            )
        result = gmail_service.test_connection()
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al probar conexión: {str(e)}")


@router.get("/analyze")
def analyze_emails():
    """Analizar el correo más reciente y extraer información de PDFs adjuntos."""
    try:
        gmail_service = get_gmail_service()
        
        if not gmail_service.is_authenticated():
            raise HTTPException(
                status_code=401,
                detail="No autenticado. Por favor inicia sesión primero en /emails/auth/login"
            )
        
        # Obtener el último correo recibido
        if not gmail_service.service:
            gmail_service.build_service()
        
        results = gmail_service.service.users().messages().list(
            userId='me',
            maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron correos"
            )
        
        # Analizar el correo más reciente
        latest_message_id = messages[0]['id']
        extraction_service = get_extraction_service()
        result = extraction_service.analyze_email_with_pdfs(latest_message_id)
        
        return {
            "status": "success",
            "result": result
        }
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar correo: {str(e)}")

