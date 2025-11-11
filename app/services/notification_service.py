import asyncio
import json
import logging
from typing import Optional

from google.cloud import pubsub_v1
from google.api_core.exceptions import NotFound

from app.core.config import get_settings
from app.services.websocket_manager import WebSocketManager
from app.services.gmail_service import get_gmail_service
from app.services.extraction_service import get_extraction_service
from app.services.label_service import get_label_service


logger = logging.getLogger(__name__)


class GmailNotificationService:
    """Gestiona suscripción a Pub/Sub para notificaciones de Gmail."""

    def __init__(self, ws_manager: WebSocketManager) -> None:
        self._settings = get_settings()
        self._ws_manager = ws_manager
        self._subscriber: Optional[pubsub_v1.SubscriberClient] = None
        self._streaming_future: Optional[pubsub_v1.subscriber.futures.StreamingPullFuture] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._gmail_service = get_gmail_service()
        self._extraction_service = get_extraction_service()
        self._label_service = get_label_service()

    async def _process_new_email(self, history_id: str) -> None:
        """Procesar nuevo correo cuando llega una notificación."""
        try:
            if not self._gmail_service.service:
                self._gmail_service.build_service()
            
            # Obtener el correo más reciente
            results = self._gmail_service.service.users().messages().list(
                userId='me',
                maxResults=1
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                logger.warning("No se encontraron mensajes nuevos")
                return
            
            latest_message_id = messages[0]['id']
            logger.info(f"Procesando correo automáticamente: {latest_message_id}")
            
            # Extraer datos estructurados
            result = self._extraction_service.extract_structured_data(latest_message_id, debug=False)
            
            # Aplicar etiqueta según la clasificación
            tipo_documento = result.get('tipo_documento', '').upper()
            if tipo_documento in ['PO', 'QUOTE']:
                try:
                    self._label_service.apply_label_to_message(latest_message_id, tipo_documento)
                    result['etiqueta_aplicada'] = tipo_documento
                except Exception as e:
                    result['etiqueta_aplicada'] = None
                    result['error_etiqueta'] = str(e)
            
            # Enviar resultado por WebSocket
            notification = {
                "type": "new_email_processed",
                "message_id": latest_message_id,
                "history_id": history_id,
                "result": result
            }
            
            if self._ws_manager:
                await self._ws_manager.broadcast(notification)
            
            logger.info(f"Correo procesado exitosamente: {latest_message_id}, tipo: {tipo_documento}")
            
        except Exception as exc:
            logger.exception("Error procesando nuevo correo: %s", exc)
            error_notification = {
                "type": "processing_error",
                "error": str(exc),
                "history_id": history_id
            }
            if self._ws_manager:
                await self._ws_manager.broadcast(error_notification)

    def start(self) -> None:
        """Inicia escucha de notificaciones Pub/Sub."""
        subscription_path = self._settings.GMAIL_PUBSUB_SUBSCRIPTION_PATH
        if not subscription_path:
            logger.warning("Pub/Sub no configurado; omitiendo escucha de notificaciones.")
            return

        if self._streaming_future:
            logger.info("Servicio de notificaciones ya estaba iniciado.")
            return

        self._loop = asyncio.get_event_loop()
        self._subscriber = pubsub_v1.SubscriberClient()

        def callback(message: pubsub_v1.subscriber.message.Message) -> None:
            try:
                data = {}
                if message.data:
                    try:
                        data = json.loads(message.data.decode("utf-8"))
                    except json.JSONDecodeError:
                        logger.warning("No se pudo decodificar el payload Pub/Sub como JSON.")
                
                attrs = dict(message.attributes or {})
                history_id = attrs.get('historyId') or data.get('historyId', '')
                
                logger.info(f"Notificación recibida de Gmail. History ID: {history_id}")
                
                # Procesar el correo automáticamente
                if self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self._process_new_email(history_id),
                        self._loop,
                    )
                
                message.ack()
            except Exception as exc:
                logger.exception("Error procesando notificación Pub/Sub: %s", exc)
                message.nack()

        try:
            self._streaming_future = self._subscriber.subscribe(subscription_path, callback=callback)
            logger.info("Suscripción Pub/Sub iniciada en %s", subscription_path)
        except NotFound:
            logger.error("Suscripción Pub/Sub %s no encontrada.", subscription_path)
        except Exception as exc:
            logger.exception("No se pudo iniciar la suscripción Pub/Sub: %s", exc)

    async def stop(self) -> None:
        """Detiene escucha de notificaciones."""
        if self._streaming_future:
            self._streaming_future.cancel()
            self._streaming_future = None
        if self._subscriber:
            await self._close_subscriber()

    async def _close_subscriber(self) -> None:
        if self._subscriber:
            self._subscriber.close()
            self._subscriber = None

