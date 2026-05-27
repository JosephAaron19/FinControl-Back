from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from .models import Asistencia, JornadaConfiguracion, HistorialJornada, JornadaActividad, UsuarioHorario, Horario, HorarioDetalle, IntercambioHorario
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def send_ws_notification(group_name, message, notification_type):
    channel_layer = get_channel_layer()
    if channel_layer:
        payload = {
            'type': 'send_notification',
            'message': message,
            'notification_type': notification_type
        }
        async_to_sync(channel_layer.group_send)(group_name, payload)
        if group_name != "system_notifications":
            async_to_sync(channel_layer.group_send)("system_notifications", payload)
        print(f"WS Notification sent to {group_name} and system_notifications: {message}")


@receiver(post_save, sender=Asistencia)
def notify_attendance_update(sender, instance, created, **kwargs):
    if instance.usuario and instance.usuario.sede_id:
        group_name = f"sede_{instance.usuario.sede_id}"
        send_ws_notification(
            group_name,
            f"Actualización de asistencia para {instance.usuario.nombre_completo}",
            "attendance_update"
        )


@receiver(post_save, sender=HistorialJornada)
def notify_history_update(sender, instance, created, **kwargs):
    if instance.usuario and instance.usuario.sede_id:
        group_name = f"sede_{instance.usuario.sede_id}"
        send_ws_notification(
            group_name,
            f"La jornada de {instance.usuario.nombre_completo} ha sido actualizada.",
            "attendance_update"
        )


@receiver(post_save, sender=JornadaConfiguracion)
def notify_config_update(sender, instance, created, **kwargs):
    if instance.sede_id:
        group_name = f"sede_{instance.sede_id}"
        send_ws_notification(
            group_name,
            "Se ha actualizado la configuración de la jornada.",
            "config_update"
        )


@receiver(post_save, sender=JornadaActividad)
def notify_activity_update(sender, instance, created, **kwargs):
    if instance.usuario and instance.usuario.sede_id:
        group_name = f"sede_{instance.usuario.sede_id}"
        status = "iniciada" if instance.estado_actividad == 'en_proceso' else "finalizada"
        send_ws_notification(
            group_name,
            f"Actividad {status}: {instance.titulo} ({instance.usuario.nombre_completo})",
            "attendance_update"
        )


@receiver(post_save, sender=UsuarioHorario)
def notify_usuario_horario_update(sender, instance, created, **kwargs):
    """
    Notifica a la app móvil cuando se asigna, cambia o extiende el horario de un usuario.
    Cubre edición y creación de asignaciones (UsuarioHorario).
    """
    try:
        if instance.usuario and instance.usuario.sede_id:
            group_name = f"sede_{instance.usuario.sede_id}"
            action = "asignado" if created else "actualizado"
            send_ws_notification(
                group_name,
                f"Horario {action} para {instance.usuario.nombre_completo}: {instance.horario.nombre if instance.horario else ''}",
                "config_update"
            )
    except Exception:
        pass


@receiver(post_save, sender=Horario)
def notify_horario_update(sender, instance, created, **kwargs):
    """
    Notifica a todos los usuarios de la sede cuando se edita o crea un horario maestro.
    """
    try:
        if instance.sede_id:
            group_name = f"sede_{instance.sede_id}"
            action = "creado" if created else "actualizado"
            send_ws_notification(
                group_name,
                f"Horario {action}: {instance.nombre}",
                "config_update"
            )
    except Exception:
        pass


@receiver(post_save, sender=HorarioDetalle)
def notify_horario_detalle_update(sender, instance, created, **kwargs):
    """
    Notifica a todos los usuarios de la sede cuando cambian los días/horas de un turno.
    """
    try:
        if instance.horario and instance.horario.sede_id:
            group_name = f"sede_{instance.horario.sede_id}"
            send_ws_notification(
                group_name,
                f"Horario '{instance.horario.nombre}': horas del {instance.dia_semana} actualizadas.",
                "config_update"
            )
    except Exception:
        pass


@receiver(post_save, sender=IntercambioHorario)
def notify_intercambio_horario_update(sender, instance, created, **kwargs):
    """
    Notifica a los usuarios involucrados en un intercambio/extensión de horario.
    Notifica a la sede del solicitante y también a la sede del reemplazo si es diferente.
    """
    try:
        notified_groups = set()

        # Notificar sede del usuario solicitante
        if instance.usuario_solicitante and instance.usuario_solicitante.sede_id:
            group_name = f"sede_{instance.usuario_solicitante.sede_id}"
            if group_name not in notified_groups:
                notified_groups.add(group_name)
                action = "creado" if created else f"actualizado (estado: {instance.estado})"
                send_ws_notification(
                    group_name,
                    f"Intercambio de horario {action}: {instance.usuario_solicitante.nombre_completo}",
                    "config_update"
                )

        # Notificar sede del usuario reemplazo (si es diferente)
        if instance.usuario_reemplazo and instance.usuario_reemplazo.sede_id:
            group_name = f"sede_{instance.usuario_reemplazo.sede_id}"
            if group_name not in notified_groups:
                notified_groups.add(group_name)
                action = "creado" if created else f"actualizado (estado: {instance.estado})"
                send_ws_notification(
                    group_name,
                    f"Intercambio de horario {action}: {instance.usuario_reemplazo.nombre_completo}",
                    "config_update"
                )
    except Exception:
        pass

