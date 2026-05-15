from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Asistencia, JornadaConfiguracion, HistorialJornada, JornadaActividad
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def send_ws_notification(group_name, message, notification_type):
    channel_layer = get_channel_layer()
    if channel_layer:
        # Payload para el método send_notification del consumer
        payload = {
            'type': 'send_notification',
            'message': message,
            'notification_type': notification_type
        }
        
        # Enviar al grupo específico (sede)
        async_to_sync(channel_layer.group_send)(group_name, payload)
        
        # Enviar también al grupo global para monitoreo/dashboard
        if group_name != "system_notifications":
            async_to_sync(channel_layer.group_send)("system_notifications", payload)
        
        print(f"WS Notification sent to {group_name} and system_notifications: {message}")

@receiver(post_save, sender=Asistencia)
def notify_attendance_update(sender, instance, created, **kwargs):
    # Notificar a la sede del usuario para que la App Móvil se refresque
    if instance.usuario and instance.usuario.sede_id:
        group_name = f"sede_{instance.usuario.sede_id}"
        send_ws_notification(
            group_name, 
            f"Actualización de asistencia para {instance.usuario.nombre_completo}", 
            "attendance_update"
        )

@receiver(post_save, sender=HistorialJornada)
def notify_history_update(sender, instance, created, **kwargs):
    # Notificar a la sede si se actualiza el historial (jornada creada/modificada)
    if instance.usuario and instance.usuario.sede_id:
        group_name = f"sede_{instance.usuario.sede_id}"
        send_ws_notification(
            group_name, 
            f"La jornada de {instance.usuario.nombre_completo} ha sido actualizada.", 
            "attendance_update"
        )

@receiver(post_save, sender=JornadaConfiguracion)
def notify_config_update(sender, instance, created, **kwargs):
    # Notificar a la sede afectada cuando cambian los horarios maestros
    if instance.sede_id:
        group_name = f"sede_{instance.sede_id}"
        send_ws_notification(
            group_name, 
            "Se ha actualizado la configuración de la jornada.", 
            "config_update"
        )
@receiver(post_save, sender=JornadaActividad)
def notify_activity_update(sender, instance, created, **kwargs):
    # Notificar a la sede cuando hay actividad de campo
    if instance.usuario and instance.usuario.sede_id:
        group_name = f"sede_{instance.usuario.sede_id}"
        status = "iniciada" if instance.estado_actividad == 'en_proceso' else "finalizada"
        send_ws_notification(
            group_name, 
            f"Actividad {status}: {instance.titulo} ({instance.usuario.nombre_completo})", 
            "attendance_update"
        )
