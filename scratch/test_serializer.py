import os
import sys
import django

# Add the parent directory to the path so django settings can be loaded
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import UsuarioHorario
from api.serializers import UsuarioHorarioSerializer

uh = UsuarioHorario.objects.all().first()
if uh:
    serializer = UsuarioHorarioSerializer(uh)
    print("Serialized data:")
    for key, value in serializer.data.items():
        print(f"{key}: {value} (type: {type(value).__name__})")
else:
    print("No UsuarioHorario record found in database.")
