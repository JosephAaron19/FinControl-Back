from django.core.management.base import BaseCommand
from api.models import Usuario
from api.firebase_service import send_push_notification

class Command(BaseCommand):
    help = 'Envía una notificación push de prueba a un usuario específico'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True, help='ID del usuario a notificar')
        parser.add_argument('--title', type=str, default='Notificación de prueba', help='Título de la notificación')
        parser.add_argument('--body', type=str, default='Esta es una notificación push de prueba desde FinControl-Back', help='Cuerpo de la notificación')

    def handle(self, *args, **options):
        user_id = options['user_id']
        title = options['title']
        body = options['body']

        try:
            user = Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Usuario con ID {user_id} no existe."))
            return

        if not user.fcm:
            self.stdout.write(self.style.WARNING(f"El usuario {user.nombre_completo} (ID: {user_id}) no tiene un token FCM guardado en base de datos."))
            return

        self.stdout.write(f"Enviando notificación a {user.nombre_completo} (ID: {user_id}) con token: {user.fcm}...")
        result = send_push_notification(
            user=user,
            title=title,
            body=body,
            data={
                "type": "prueba",
                "test_key": "test_value"
            }
        )

        if result:
            self.stdout.write(self.style.SUCCESS(f"Notificación enviada exitosamente. ID del mensaje: {result}"))
        else:
            self.stdout.write(self.style.ERROR("Falló el envío de la notificación. Revisa los logs para más detalles."))
