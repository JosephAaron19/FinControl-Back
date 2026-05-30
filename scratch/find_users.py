import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

def list_users():
    print("--- Listing active users ---")
    users = Usuario.objects.all()
    for u in users:
         print(f"DNI: {u.dni} | Nombre: {u.nombre_completo} | Rol: {u.rol.nombre if u.rol else 'None'} | Activo: {u.activo}")

if __name__ == '__main__':
    list_users()
