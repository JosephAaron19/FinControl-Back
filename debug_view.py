import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.views import ActividadDetalleUsuarioView
from api.models import Usuario
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

factory = APIRequestFactory()
request = factory.get('/api/actividad/usuario/1/')

# Obtener usuario para autenticar (preferiblemente admin o el que tenga el rol Superadmin)
admin = Usuario.objects.filter(rol__nombre__icontains='superadmin').first()
if not admin:
    admin = Usuario.objects.first()

force_authenticate(request, user=admin)

view = ActividadDetalleUsuarioView.as_view()
try:
    response = view(request, pk=1)
    print("Response Status:", response.status_code)
    print("Response Data:", response.data)
except Exception as e:
    import traceback
    traceback.print_exc()
