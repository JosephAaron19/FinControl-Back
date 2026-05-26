import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

print("=== RESTABLECIENDO CONTRASEÑA DE ADMINISTRADOR ===")
admin_user = Usuario.objects.filter(dni='admin').first()
if not admin_user:
    print("[!] El usuario 'admin' no existe.")
else:
    admin_user.set_password('123456')
    admin_user.save()
    print("[OK] Contraseña para 'admin' restablecida a '123456' con éxito!")
print("==================================================")
