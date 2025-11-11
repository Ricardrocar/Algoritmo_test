import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from email.utils import parsedate_to_datetime
from app.services.gmail_service import get_gmail_service
from app.services.pdf_service import get_pdf_service
from app.services.classification_service import get_classification_service
from app.utils.text_utils import clean_text, truncate_text, html_to_text

class ExtractionService:
    """Servicio para extraer información de correos y PDFs."""
    
    def __init__(self):
        self.gmail_service = get_gmail_service()
        self.pdf_service = get_pdf_service()
        self.classification_service = get_classification_service()
    
    def extract_email_info(self, message_id: str) -> Dict[str, Any]:
        """Extraer información de un correo electrónico."""
        if not self.gmail_service.service:
            self.gmail_service.build_service()
        
        message = self.gmail_service.service.users().messages().get(
            userId='me', id=message_id, format='full'
        ).execute()
        
        payload = message.get('payload', {})
        headers = {h['name']: h['value'] for h in payload.get('headers', [])}
        body_text = self._extract_message_body(payload)
        
        return {
            "message_id": message_id,
            "thread_id": message.get('threadId'),
            "subject": headers.get('Subject', ''),
            "from": headers.get('From', ''),
            "to": headers.get('To', ''),
            "date": headers.get('Date', ''),
            "body": body_text,
            "body_preview": truncate_text(body_text, 200),
            "snippet": message.get('snippet', ''),
            "attachments": self._extract_attachments(payload)
        }
    
    def _extract_message_body(self, payload: Dict) -> str:
        import base64
        body_text = ""
        html_content = ""
        
        parts = payload.get('parts', [payload]) if 'parts' in payload else [payload]
        for part in parts:
            mime = part.get('mimeType', '')
            data = part.get('body', {}).get('data', '')
            if not data:
                continue
            
            try:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            except:
                continue
            
            if mime == 'text/plain':
                body_text += decoded + "\n"
            elif mime == 'text/html':
                html_content += decoded
        
        if html_content:
            body_text = html_to_text(html_content)
        elif body_text:
            body_text = clean_text(body_text)
        
        return body_text
    
    def _extract_attachments(self, payload: Dict) -> List[Dict[str, Any]]:
        """Extraer información de adjuntos."""
        return [
            {
                "filename": part.get('filename', ''),
                "attachment_id": part.get('body', {}).get('attachmentId', ''),
                "size": part.get('body', {}).get('size', 0),
                "mime_type": part.get('mimeType', ''),
                "is_pdf": part.get('mimeType', '') == 'application/pdf'
            }
            for part in payload.get('parts', []) if part.get('filename')
        ]
    
    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Descargar un adjunto de un correo."""
        import base64
        if not self.gmail_service.service:
            self.gmail_service.build_service()
        
        attachment = self.gmail_service.service.users().messages().attachments().get(
            userId='me', messageId=message_id, id=attachment_id
        ).execute()
        return base64.urlsafe_b64decode(attachment['data'])
    
    def analyze_email_with_pdfs(self, message_id: str) -> Dict[str, Any]:
        """Analizar un correo y extraer información de PDFs adjuntos."""
        email_info = self.extract_email_info(message_id)
        pdf_results = []
        
        for att in email_info.get('attachments', []):
            if att.get('is_pdf'):
                try:
                    pdf_data = self.download_attachment(message_id, att['attachment_id'])
                    pdf_info = self.pdf_service.process_pdf(pdf_data)
                    pdf_results.append({
                        "filename": att['filename'],
                        "text": pdf_info['text'],
                        "metadata": pdf_info['metadata'],
                        "text_length": pdf_info['text_length'],
                        "has_text": pdf_info['has_text']
                    })
                except Exception as e:
                    pdf_results.append({"filename": att['filename'], "error": str(e)})
        
        return {
            "email": email_info,
            "pdfs": pdf_results,
            "total_pdfs": len([p for p in pdf_results if 'error' not in p]),
            "total_pdfs_with_text": len([p for p in pdf_results if p.get('has_text', False)])
        }
    
    def extract_structured_data(self, message_id: str, debug: bool = False) -> Dict[str, Any]:
        """Extraer datos estructurados del correo en formato PO/QUOTE."""
        email_info = self.extract_email_info(message_id)
        subject, body = email_info.get('subject', ''), email_info.get('body', '')
        
        all_pdf_texts = []
        for att in email_info.get('attachments', []):
            if att.get('is_pdf'):
                try:
                    pdf_data = self.download_attachment(message_id, att['attachment_id'])
                    all_pdf_texts.append(self.pdf_service.process_pdf(pdf_data).get('text', ''))
                except:
                    continue
        
        pdf_combined = ' '.join(all_pdf_texts)
        combined_text = f"{subject} {body} {pdf_combined}"
        
        tipo_documento = self.classification_service.classify_document(subject, body, pdf_combined)
        productos = []
        
        for pdf_text in all_pdf_texts:
            productos.extend(self.classification_service.extract_products_from_text(pdf_text))
        
        if not productos:
            productos = self.classification_service.extract_products_from_text(body)
        else:
            body_products = self.classification_service.extract_products_from_text(body)
            if body_products:
                productos.extend(body_products)
        
        totals_data = self.classification_service.extract_totals_from_text(combined_text)
        if totals_data["total"] == 0.0 and productos:
            totals_data["total"] = sum(p.get("total", 0) for p in productos)
        
        result = {
            "tipo_documento": tipo_documento,
            "correo": self._extract_email_address(email_info.get('from', '')),
            "asunto": subject,
            "fecha": self._parse_date_to_iso(email_info.get('date', '')),
            "productos": productos,
            "totales": totals_data,
            "adjuntos": [{"nombre": a.get('filename', ''), "tipo": a.get('mime_type', '')} 
                         for a in email_info.get('attachments', [])]
        }
        
        if debug:
            result['debug'] = {
                "subject": subject, "body_preview": body[:500], "body_length": len(body),
                "pdf_count": len(all_pdf_texts), "pdf_text_preview": pdf_combined[:500],
                "pdf_text_length": len(pdf_combined)
            }
        
        return result
    
    def _parse_date_to_iso(self, date_str: str) -> str:
        """Convertir fecha de Gmail a formato ISO 8601."""
        try:
            return parsedate_to_datetime(date_str).isoformat() if date_str else datetime.now().isoformat()
        except:
            return datetime.now().isoformat()
    
    def _extract_email_address(self, from_field: str) -> str:
        """Extraer dirección de email del campo 'From'."""
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_field)
        return match.group(0) if match else from_field
    
    def search_emails_with_pdfs(self, query: str = "has:attachment filename:pdf", max_results: int = 10) -> List[Dict[str, Any]]:
        """Buscar correos con PDFs adjuntos."""
        if not self.gmail_service.service:
            self.gmail_service.build_service()
        
        messages = self.gmail_service.service.users().messages().list(
            userId='me', q=query, maxResults=max_results
        ).execute().get('messages', [])
        
        analyzed_emails = []
        for msg in messages:
            try:
                analyzed_emails.append(self.analyze_email_with_pdfs(msg['id']))
            except Exception as e:
                analyzed_emails.append({"message_id": msg['id'], "error": str(e)})
        
        return analyzed_emails
_extraction_service_instance: Optional[ExtractionService] = None

def get_extraction_service() -> ExtractionService:
    """Obtener o crear instancia del servicio de extracción."""
    global _extraction_service_instance
    if _extraction_service_instance is None:
        _extraction_service_instance = ExtractionService()
    return _extraction_service_instance
