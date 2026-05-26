import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

def inspect():
    print("=== INSPECTING USERS AND ROLES ===")
    for u in Usuario.objects.all().select_related('rol', 'sede'):
        role_name = u.rol.nombre if u.rol else 'NO ROLE'
        sede_name = u.sede.nombre if u.sede else 'NO SEDE'
        print(f"ID: {u.id} | DNI: {u.dni} | Name: {u.nombre_completo} | Role: {role_name} | Sede: {sede_name}")

if __name__ == '__main__':
    inspect()
