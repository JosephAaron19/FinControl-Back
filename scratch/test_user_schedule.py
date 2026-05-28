import os
import sys
import django

# Add the parent directory to the path so django settings can be loaded
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario
from api.views import JornadaEstadoMarcacionView
from rest_framework.test import APIRequestFactory, force_authenticate

# Authenticate as prueba1 (DNI: 88888888)
user = Usuario.objects.get(dni='88888888')
factory = APIRequestFactory()
request = factory.get('/api/jornada/estado-marcacion/')
force_authenticate(request, user=user)

view = JornadaEstadoMarcacionView.as_view()
response = view(request)

print("Status Code:", response.status_code)
import json
print("Response Body:")
print(json.dumps(response.data, indent=2))
