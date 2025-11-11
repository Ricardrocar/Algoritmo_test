import re
from typing import Dict, List, Any, Optional
from app.services.gmail_service import get_gmail_service
from app.services.pdf_service import get_pdf_service
from app.utils.text_utils import clean_text, truncate_text


class ExtractionService:
    """Servicio para extraer información de correos y PDFs."""
    
    def __init__(self):
        self.gmail_service = get_gmail_service()
        self.pdf_service = get_pdf_service()
    
    def extract_email_info(self, message_id: str) -> Dict[str, Any]:
        """Extraer información de un correo electrónico."""
        try:
            if not self.gmail_service.service:
                self.gmail_service.build_service()
            
            message = self.gmail_service.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message.get('payload', {}).get('headers', [])
            headers_dict = {h['name']: h['value'] for h in headers}
            body_text = self._extract_message_body(message.get('payload', {}))
            
            return {
                "message_id": message_id,
                "thread_id": message.get('threadId'),
                "subject": headers_dict.get('Subject', ''),
                "from": headers_dict.get('From', ''),
                "to": headers_dict.get('To', ''),
                "date": headers_dict.get('Date', ''),
                "body": body_text,
                "body_preview": truncate_text(body_text, 200),
                "snippet": message.get('snippet', ''),
                "attachments": self._extract_attachments(message.get('payload', {}))
            }
        except Exception as e:
            raise ValueError(f"Error al extraer información del correo: {str(e)}")
    
    def _extract_message_body(self, payload: Dict) -> str:
        """Extraer el texto del cuerpo del mensaje."""
        body_text = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        import base64
                        body_text += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part.get('mimeType') == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data and not body_text:
                        import base64
                        html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        body_text += re.sub(r'<[^>]+>', '', html)
        else:
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data', '')
                if data:
                    import base64
                    body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return clean_text(body_text)
    
    def _extract_attachments(self, payload: Dict) -> List[Dict[str, Any]]:
        """Extraer información de adjuntos."""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                filename = part.get('filename', '')
                if filename:
                    attachment_id = part.get('body', {}).get('attachmentId', '')
                    size = part.get('body', {}).get('size', 0)
                    mime_type = part.get('mimeType', '')
                    
                    attachments.append({
                        "filename": filename,
                        "attachment_id": attachment_id,
                        "size": size,
                        "mime_type": mime_type,
                        "is_pdf": mime_type == 'application/pdf'
                    })
        
        return attachments
    
    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Descargar un adjunto de un correo."""
        try:
            if not self.gmail_service.service:
                self.gmail_service.build_service()
            attachment = self.gmail_service.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            import base64
            file_data = base64.urlsafe_b64decode(attachment['data'])
            return file_data
        except Exception as e:
            raise ValueError(f"Error al descargar adjunto: {str(e)}")
    
    def analyze_email_with_pdfs(self, message_id: str) -> Dict[str, Any]:
        """Analizar un correo y extraer información de PDFs adjuntos."""
        try:
            email_info = self.extract_email_info(message_id)
            pdf_results = []
            for attachment in email_info.get('attachments', []):
                if attachment.get('is_pdf'):
                    try:
                        pdf_data = self.download_attachment(message_id, attachment['attachment_id'])
                        pdf_info = self.pdf_service.process_pdf(pdf_data)
                        
                        pdf_results.append({
                            "filename": attachment['filename'],
                            "text": pdf_info['text'],
                            "metadata": pdf_info['metadata'],
                            "text_length": pdf_info['text_length'],
                            "has_text": pdf_info['has_text']
                        })
                    except Exception as e:
                        pdf_results.append({
                            "filename": attachment['filename'],
                            "error": str(e)
                        })
            
            return {
                "email": email_info,
                "pdfs": pdf_results,
                "total_pdfs": len([p for p in pdf_results if 'error' not in p]),
                "total_pdfs_with_text": len([p for p in pdf_results if p.get('has_text', False)])
            }
        except Exception as e:
            raise ValueError(f"Error al analizar correo con PDFs: {str(e)}")
    
    def search_emails_with_pdfs(self, query: str = "has:attachment filename:pdf", max_results: int = 10) -> List[Dict[str, Any]]:
        """Buscar correos con PDFs adjuntos."""
        try:
            if not self.gmail_service.service:
                self.gmail_service.build_service()
            
            results = self.gmail_service.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            analyzed_emails = []
            
            for msg in messages:
                try:
                    analysis = self.analyze_email_with_pdfs(msg['id'])
                    analyzed_emails.append(analysis)
                except Exception as e:
                    analyzed_emails.append({
                        "message_id": msg['id'],
                        "error": str(e)
                    })
            
            return analyzed_emails
        except Exception as e:
            raise ValueError(f"Error al buscar correos con PDFs: {str(e)}")

_extraction_service_instance: Optional[ExtractionService] = None

def get_extraction_service() -> ExtractionService:
    """Obtener o crear instancia del servicio de extracción."""
    global _extraction_service_instance
    if _extraction_service_instance is None:
        _extraction_service_instance = ExtractionService()
    return _extraction_service_instance

