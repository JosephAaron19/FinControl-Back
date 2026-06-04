import os
import sys
import django

# Add the parent directory to the path so django settings can be loaded
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario, Horario, UsuarioHorario
from datetime import date

try:
    user = Usuario.objects.filter(nombre_completo__icontains='prueba').first()
    horario = Horario.objects.filter(activo=True).first()
    print("User found:", user)
    print("Horario found:", horario)
    if user and horario:
        # Try to create UsuarioHorario
        uh = UsuarioHorario.objects.create(
            usuario=user,
            horario=horario,
            sede_id=user.sede_id or horario.sede_id,
            vigente_desde=date.today(),
            es_principal=True,
            activo=True,
            observacion='Test script assignment'
        )
        print("Success! Created UsuarioHorario:", uh)
        # Delete it to keep DB clean
        uh.delete()
        print("Deleted test assignment.")
except Exception as e:
    import traceback
    traceback.print_exc()
