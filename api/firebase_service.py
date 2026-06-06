import os
import logging
import json
from django.utils import timezone
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

# Variable global para registrar si el SDK ya fue inicializado
_firebase_initialized = False

def initialize_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return True
        
    credentials_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'config/firebase-service-account.json')
    
    # Si la ruta es relativa, resolverla respecto al directorio base del proyecto (settings.BASE_DIR)
    if not os.path.isabs(credentials_path):
        credentials_path = os.path.join(settings.BASE_DIR, credentials_path)
        
    if not os.path.exists(credentials_path):
        logger.error(f"Archivo de credenciales de Firebase no encontrado en: {credentials_path}")
        return False
        
    try:
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin SDK inicializado correctamente.")
        return True
    except Exception as e:
        logger.error(f"Error al inicializar Firebase Admin SDK: {e}")
        return False

def send_push_notification(user, title, body, data=None):
    """
    Envía una notificación push a un usuario usando Firebase Admin SDK.
    Registra cada envío en la tabla notificaciones_push para auditoría.
    """
    from .models import NotificacionPush  # Importación tardía para evitar importación circular

    fcm_token = user.fcm
    if not fcm_token or str(fcm_token).strip() == '':
        logger.warning(f"El usuario {user.id} ({user.nombre_completo}) no tiene token FCM registrado.")
        return None

    # Inicializar Firebase Admin SDK
    if not initialize_firebase():
        logger.error("No se puede enviar la notificación por fallo en inicialización de Firebase.")
        return None

    # Formatear todos los valores de 'data' a string, obligatorio para Firebase Messaging
    formatted_data = {}
    if data:
        for k, v in data.items():
            formatted_data[str(k)] = str(v)

    # Crear auditoría en estado PENDIENTE
    audit = NotificacionPush.objects.create(
        usuario=user,
        fcm_token=fcm_token,
        titulo=title,
        mensaje=body,
        tipo=data.get('type') if data else None,
        payload=json.dumps(data) if data else None,
        estado='PENDIENTE'
    )

    try:
        # Construcción del mensaje push
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=formatted_data,
            token=fcm_token,
        )
        
        # Enviar notificación
        response = messaging.send(message)
        logger.info(f"Notificación enviada con éxito a usuario {user.id}. Message ID: {response}")
        
        # Actualizar auditoría a ENVIADA
        audit.estado = 'ENVIADA'
        audit.fecha_envio = timezone.now()
        audit.save(update_fields=['estado', 'fecha_envio'])
        return response
        
    except Exception as e:
        logger.error(f"Error al enviar notificación Firebase a usuario {user.id}: {e}")
        
        # Actualizar auditoría a ERROR y registrar detalle
        audit.estado = 'ERROR'
        audit.error = str(e)
        audit.save(update_fields=['estado', 'error'])
        return None
