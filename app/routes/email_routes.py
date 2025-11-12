from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from app.services.gmail_service import get_gmail_service
from app.services.extraction_service import get_extraction_service
from app.services.label_service import get_label_service
import json
import csv
import io
import zipfile

router = APIRouter(prefix="/emails", tags=["emails"])
_oauth_flows = {}
@router.get("/auth/status")
def auth_status():
    gmail_service = get_gmail_service()
    is_auth = gmail_service.is_authenticated()
    return {
        "authenticated": is_auth,
        "message": "Usuario autenticado" if is_auth else "Usuario necesita autenticarse"
    }

@router.get("/auth/login")
def login():
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
                    scopes=settings.GMAIL_SCOPES_LIST,
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
def analyze_emails(debug: bool = False, download: bool = True):
    try:
        gmail_service = get_gmail_service()
        
        if not gmail_service.is_authenticated():
            raise HTTPException(
                status_code=401,
                detail="No autenticado. Por favor inicia sesión primero en /emails/auth/login"
            )
        
        if not gmail_service.service:
            gmail_service.build_service()
        
        results = gmail_service.service.users().messages().list(
            userId='me',
            maxResults=20
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron correos"
            )
        
        all_messages = []
        for msg in messages:
            msg_detail = gmail_service.service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Date']
            ).execute()
            all_messages.append({
                'id': msg['id'],
                'internalDate': int(msg_detail.get('internalDate', 0))
            })
        
        all_messages.sort(key=lambda x: x['internalDate'], reverse=True)
        latest_message_id = all_messages[0]['id']
        extraction_service = get_extraction_service()
        result = extraction_service.extract_structured_data(latest_message_id, debug=debug)
        tipo_documento = result.get('tipo_documento', '').upper()
        if tipo_documento in ['PO', 'QUOTE']:
            try:
                label_service = get_label_service()
                label_service.apply_label_to_message(latest_message_id, tipo_documento)
            except Exception:
                pass
        
        result.pop('etiqueta_aplicada', None)
        result.pop('error_etiqueta', None)
        result.pop('email_json', None)
        
        if not download:
            return JSONResponse(content=result)
        
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
        
        csv_output = io.StringIO()
        csv_writer = csv.writer(csv_output)
        
        csv_writer.writerow(['tipo_documento', result.get('tipo_documento', '')])
        csv_writer.writerow(['correo', result.get('correo', '')])
        csv_writer.writerow(['asunto', result.get('asunto', '')])
        csv_writer.writerow(['fecha', result.get('fecha', '')])
        csv_writer.writerow(['total', result.get('totales', {}).get('total', '')])
        csv_writer.writerow(['moneda', result.get('totales', {}).get('moneda', '')])
        csv_writer.writerow([])
        
        csv_writer.writerow(['Productos'])
        csv_writer.writerow(['nombre', 'cantidad', 'precio_unitario', 'total'])
        for producto in result.get('productos', []):
            csv_writer.writerow([
                producto.get('nombre', ''),
                producto.get('cantidad', ''),
                producto.get('precio_unitario', ''),
                producto.get('total', '')
            ])
        
        csv_writer.writerow([])
        csv_writer.writerow(['Adjuntos'])
        csv_writer.writerow(['nombre', 'tipo'])
        for adjunto in result.get('adjuntos', []):
            csv_writer.writerow([
                adjunto.get('nombre', ''),
                adjunto.get('tipo', '')
            ])
        
        csv_str = csv_output.getvalue()
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f'analisis_{latest_message_id}.json', json_str.encode('utf-8'))
            zip_file.writestr(f'analisis_{latest_message_id}.csv', csv_str.encode('utf-8'))
        
        zip_buffer.seek(0)
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="analisis_{latest_message_id}.zip"',
            }
        )
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar correo: {str(e)}")
