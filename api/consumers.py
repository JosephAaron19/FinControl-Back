import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def label(self):
        return "notifications"

    async def connect(self):
        self.user = self.scope["user"]
        
        # Unirse a un grupo global para notificaciones de sistema
        await self.channel_layer.group_add(
            "system_notifications",
            self.channel_name
        )
        
        # Si el usuario está autenticado, unirse a un grupo específico de su sede
        if self.user.is_authenticated and self.user.sede:
            self.sede_group = f"sede_{self.user.sede.id}"
            await self.channel_layer.group_add(
                self.sede_group,
                self.channel_name
            )

        await self.accept()

    async def disconnect(self, close_code):
        # Salir de los grupos
        await self.channel_layer.group_discard(
            "system_notifications",
            self.channel_name
        )
        
        if hasattr(self, 'sede_group'):
            await self.channel_layer.group_discard(
                self.sede_group,
                self.channel_name
            )

    # Método para recibir mensajes del grupo
    async def send_notification(self, event):
        message = event['message']
        type = event.get('notification_type', 'info')
        
        # Enviar mensaje al WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'type': type
        }))
