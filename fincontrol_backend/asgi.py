"""
ASGI config for fincontrol_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')

import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from api.middleware import JWTAuthMiddleware
import api.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            api.routing.websocket_urlpatterns
        )
    ),
})
