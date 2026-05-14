from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Asistencia, JornadaConfiguracion, HistorialJornada
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def send_ws_notification(group_name, message, notification_type):
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'send_notification',
                'message': message,
                'notification_type': notification_type
            }
        )

@receiver(post_save, sender=Asistencia)
def notify_attendance_update(sender, instance, created, **kwargs):
    # Notificar a la sede del usuario para que la App Móvil se refresque
    if instance.usuario and instance.usuario.sede:
        group_name = f"sede_{instance.usuario.sede.id}"
        send_ws_notification(
            group_name, 
            f"Actualización de asistencia para {instance.usuario.nombre_completo}", 
            "attendance_update"
        )

@receiver(post_save, sender=HistorialJornada)
def notify_history_update(sender, instance, created, **kwargs):
    # Notificar a la sede si se actualiza el historial (jornada creada)
    if instance.usuario and instance.usuario.sede:
        group_name = f"sede_{instance.usuario.sede.id}"
        send_ws_notification(
            group_name, 
            f"La jornada de {instance.usuario.nombre_completo} ha sido actualizada.", 
            "attendance_update"
        )

@receiver(post_save, sender=JornadaConfiguracion)
def notify_config_update(sender, instance, created, **kwargs):
    # Notificar a la sede afectada cuando cambian los horarios maestros
    if instance.sede:
        group_name = f"sede_{instance.sede.id}"
        send_ws_notification(
            group_name, 
            "Se ha actualizado la configuración de la jornada.", 
            "config_update"
        )
