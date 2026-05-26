import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

print("=== RESTABLECIENDO CONTRASEÑAS DE ASESORES ===")
dnis_to_reset = ['prueba', '70043709', '60322591', '43084696']

for dni in dnis_to_reset:
    user = Usuario.objects.filter(dni=dni).first()
    if user:
        user.set_password('123456')
        user.save()
        print(f"[OK] Contraseña para '{user.nombre_completo}' (DNI: {dni}) restablecida a '123456'!")
    else:
        print(f"[!] Usuario con DNI '{dni}' no encontrado.")
print("==============================================")
