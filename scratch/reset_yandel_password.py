import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

print("=== RESETTING PASSWORD FOR YANDEL ===")
u = Usuario.objects.filter(dni='77777777').first()
if u:
    u.set_password('123456')
    u.save()
    print(f"[OK] Contraseña para '{u.nombre_completo}' (DNI: 77777777) restablecida a '123456'!")
else:
    print("[!] Usuario yandel (DNI: 77777777) no encontrado.")
print("=====================================")
