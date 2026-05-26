import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

print("--- Usuarios y Roles ---")
for u in Usuario.objects.all():
    print(f"DNI: {u.dni} | Nombre: {u.nombre_completo} | Rol: {u.rol.nombre if u.rol else 'Sin Rol'} | Activo: {u.activo}")
