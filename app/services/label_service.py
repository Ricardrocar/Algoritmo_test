from typing import Optional
from googleapiclient.errors import HttpError
from app.services.gmail_service import get_gmail_service


class LabelService:
    """Servicio para manejar etiquetas de Gmail."""
    
    def __init__(self):
        self.gmail_service = get_gmail_service()
    
    def get_label_id(self, label_name: str) -> str:
        """Obtener el ID de una etiqueta existente en Gmail."""
        if not self.gmail_service.service:
            self.gmail_service.build_service()
        
        try:
            labels = self.gmail_service.service.users().labels().list(userId='me').execute()
            for label in labels.get('labels', []):
                if label.get('name') == label_name:
                    return label.get('id')
            raise ValueError(f"Etiqueta '{label_name}' no encontrada en Gmail")
        except HttpError as error:
            raise ValueError(f"Error al obtener etiqueta {label_name}: {error}")
    
    def apply_label_to_message(self, message_id: str, label_name: str) -> bool:
        """Aplicar una etiqueta existente y mover el correo a esa etiqueta (remover de INBOX)."""
        try:
            if not self.gmail_service.service:
                self.gmail_service.build_service()
            
            # Obtener ID de la etiqueta existente
            label_id = self.get_label_id(label_name)
            
            # Obtener ID de INBOX para removerlo
            inbox_id = self.get_label_id('INBOX')
            
            # Aplicar etiqueta y remover de INBOX (mover a la etiqueta)
            self.gmail_service.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': [label_id],
                    'removeLabelIds': [inbox_id]
                }
            ).execute()
            return True
        except HttpError as error:
            print(f"Error al aplicar etiqueta {label_name} al mensaje: {error}")
            return False
        except Exception as e:
            print(f"Error inesperado al aplicar etiqueta: {e}")
            return False


# Instancia global
_label_service_instance: Optional[LabelService] = None


def get_label_service() -> LabelService:
    """Obtener o crear instancia del servicio de etiquetas."""
    global _label_service_instance
    if _label_service_instance is None:
        _label_service_instance = LabelService()
    return _label_service_instance

