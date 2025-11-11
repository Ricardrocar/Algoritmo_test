import io
import base64
from typing import Optional, Dict, Any
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
from PyPDF2 import PdfReader


class PDFService:
    """Servicio para procesar y extraer texto de archivos PDF."""
    def __init__(self):
        pass
    def extract_text(self, pdf_data: bytes) -> str:
        """Extraer texto de PDF usando pdfminer."""
        try:
            pdf_file = io.BytesIO(pdf_data)
            laparams = LAParams()
            text = extract_text(pdf_file, laparams=laparams)
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error al extraer texto del PDF: {str(e)}")
    
    def get_pdf_metadata(self, pdf_data: bytes) -> Dict[str, Any]:
        """Obtener metadatos del PDF."""
        try:
            pdf_file = io.BytesIO(pdf_data)
            reader = PdfReader(pdf_file)
            metadata = reader.metadata or {}
            
            return {
                "num_pages": len(reader.pages),
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": str(metadata.get("/CreationDate", "")),
                "modification_date": str(metadata.get("/ModDate", ""))
            }
        except Exception as e:
            raise ValueError(f"Error al obtener metadatos del PDF: {str(e)}")
    
    def process_pdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """Procesar PDF y extraer texto y metadatos."""
        try:
            text = self.extract_text(pdf_data)
            metadata = self.get_pdf_metadata(pdf_data)
            
            return {
                "text": text,
                "metadata": metadata,
                "text_length": len(text),
                "has_text": len(text.strip()) > 0
            }
        except Exception as e:
            raise ValueError(f"Error al procesar PDF: {str(e)}")
    
    def decode_base64_pdf(self, base64_data: str) -> bytes:
        """Decodificar PDF desde base64."""
        try:
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            
            return base64.b64decode(base64_data)
        except Exception as e:
            raise ValueError(f"Error al decodificar base64: {str(e)}")

_pdf_service_instance: Optional[PDFService] = None

def get_pdf_service() -> PDFService:
    """Obtener o crear instancia del servicio de PDF."""
    global _pdf_service_instance
    if _pdf_service_instance is None:
        _pdf_service_instance = PDFService()
    return _pdf_service_instance

