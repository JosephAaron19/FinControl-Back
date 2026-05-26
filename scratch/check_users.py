import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

print("=== USUARIOS REGISTRADOS EN LA BD REMOTA ===")
usuarios = Usuario.objects.all()
if not usuarios.exists():
    print("[!] No hay usuarios en la base de datos.")
else:
    for u in usuarios:
        rol_nombre = u.rol.nombre if u.rol else 'Sin Rol'
        sede_nombre = u.sede.nombre if u.sede else 'Sin Sede'
        print(f"- DNI: {u.dni} | Nombre: {u.nombre_completo} | Rol: {rol_nombre} | Sede: {sede_nombre} | Activo: {u.is_active}")
print("==========================================")
