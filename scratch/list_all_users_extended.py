import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

print("=== ALL USERS EXTENDED ===")
for u in Usuario.objects.all().order_by('-id'):
    print(f"ID: {u.id} | DNI: '{u.dni}' | Nombre: '{u.nombre_completo}' | Rol: '{u.rol.nombre if u.rol else 'N/A'}' | Cargo: '{u.cargo}' | Activo: {u.is_active}")
print("===========================")
