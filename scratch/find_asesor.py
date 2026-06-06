import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario

print("--- Listing Asesores in Database ---")
asesores = Usuario.objects.filter(rol__nombre__icontains='asesor')
print(f"Total Asesores: {asesores.count()}")
for a in asesores[:10]:
    print(f"ID: {a.id} | DNI: {a.dni} | Nombre: {a.nombre_completo} | Activo: {a.activo} (is_active={a.is_active})")

if asesores.exists():
    target = asesores.first()
    print(f"\n[*] Resetting password of {target.nombre_completo} (DNI: {target.dni}) to '123' for testing...")
    target.set_password("123")
    target.save()
    print("[OK] Password reset complete.")
else:
    print("[!] No asesores found.")
