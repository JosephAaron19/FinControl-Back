import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Rol, Usuario

print("=== ALL ROLES IN DATABASE ===")
for r in Rol.objects.all():
    print(f"- ID: {r.id} | Código: {r.codigo} | Nombre: '{r.nombre}'")

print("\n=== USER ROLES IN DATABASE ===")
for u in Usuario.objects.all():
    rol_nombre = u.rol.nombre if u.rol else "SIN ROL"
    rol_codigo = u.rol.codigo if u.rol else "SIN ROL"
    print(f"- Usuario: {u.nombre_completo} | DNI: {u.dni} | Rol Nombre: '{rol_nombre}' | Rol Código: '{rol_codigo}' | Cargo: '{u.cargo}'")
print("==============================")
