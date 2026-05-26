import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

try:
    admin_user = Usuario.objects.get(dni='admin')
    admin_user.set_password('123456')
    admin_user.save()
    print("Contrasea de 'admin' cambiada a '123456' con xito.")
except Exception as e:
    print(f"Error: {e}")
