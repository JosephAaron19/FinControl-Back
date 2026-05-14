import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

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
        
        # Si el usuario está autenticado, unirse a los grupos de sus sedes
        if self.user.is_authenticated:
            self.groups_joined = ["system_notifications"]
            
            # 1. Sede principal del perfil
            if self.user.sede:
                sede_group = f"sede_{self.user.sede.id}"
                await self.channel_layer.group_add(sede_group, self.channel_name)
                self.groups_joined.append(sede_group)
            
            # 2. Sedes adicionales asignadas (para Gerentes/Supervisores)
            from .models import UsuarioSede
            additional_sedes = await database_sync_to_async(
                lambda: list(UsuarioSede.objects.filter(usuario=self.user).values_list('sede_id', flat=True))
            )()
            
            for sede_id in additional_sedes:
                sede_group = f"sede_{sede_id}"
                if sede_group not in self.groups_joined:
                    await self.channel_layer.group_add(sede_group, self.channel_name)
                    self.groups_joined.append(sede_group)

        await self.accept()

    async def disconnect(self, close_code):
        # Salir de todos los grupos a los que se unió
        if hasattr(self, 'groups_joined'):
            for group in self.groups_joined:
                await self.channel_layer.group_discard(group, self.channel_name)
        else:
            await self.channel_layer.group_discard("system_notifications", self.channel_name)

    # Método para recibir mensajes del grupo
    async def send_notification(self, event):
        message = event['message']
        type = event.get('notification_type', 'info')
        
        # Enviar mensaje al WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'type': type
        }))
