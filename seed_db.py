import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Rol, Sede, Usuario, TipoIncidencia

def seed():
    print("=== SEEDING DATABASE ===")
    
    # 1. Create Roles
    admin_rol, _ = Rol.objects.get_or_create(
        codigo="ADMIN",
        defaults={"nombre": "Administrador", "descripcion": "Acceso total", "activo": True}
    )
    gerente_rol, _ = Rol.objects.get_or_create(
        codigo="GERENTE",
        defaults={"nombre": "Gerente de Sede", "descripcion": "Gestión de sede", "activo": True}
    )
    trabajador_rol, _ = Rol.objects.get_or_create(
        codigo="TRABAJADOR",
        defaults={"nombre": "Trabajador", "descripcion": "Registro de asistencias", "activo": True}
    )
    print("[OK] Roles created.")

    # 2. Create Sede
    sede_central, _ = Sede.objects.get_or_create(
        nombre="Sede Central - Finhold",
        defaults={
            "direccion": "Calle Las Orquídeas 456, San Isidro",
            "latitud": -12.046374,
            "longitud": -77.042793,
            "radio_metros": 100,
            "activo": True,
            "codigo": "SEDE_CENTRAL"
        }
    )
    print("[OK] Sede Central created.")

    # 3. Create Test User (Worker)
    user, created = Usuario.objects.get_or_create(
        dni="12345678",
        defaults={
            "nombre_completo": "Juan Pérez",
            "cargo": "Analista de Sistemas",
            "sede": sede_central,
            "rol": trabajador_rol,
            "activo": True,
            "is_active": True,
            "is_staff": False
        }
    )
    if created or not user.check_password("123"):
        user.set_password("123")
        user.save()
    print("[OK] Test user '12345678' (Juan Pérez) created/updated.")

    # 4. Create Superuser (Admin)
    superuser, created = Usuario.objects.get_or_create(
        dni="87654321",
        defaults={
            "nombre_completo": "Administrador Sistema",
            "cargo": "Administrador",
            "sede": sede_central,
            "rol": admin_rol,
            "activo": True,
            "is_active": True,
            "is_staff": True,
            "is_superuser": True
        }
    )
    if created or not superuser.check_password("admin123"):
        superuser.set_password("admin123")
        superuser.save()
    print("[OK] Superuser '87654321' (admin123) created/updated.")

    # 5. Create default incident types
    incident_types = [
        ("TARDANZA_JUSTIFICADA", "Tardanza Justificada", "Retraso con justificación previa", True),
        ("FALLA_EQUIPO", "Falla de Equipo", "Problemas técnicos con el dispositivo móvil", True),
        ("SALIDA_ANTICIPADA", "Salida Anticipada", "Retiro antes del fin de la jornada", True),
        ("OTRO", "Otro", "Otras incidencias generales", False),
    ]
    for codigo, nombre, desc, req_ev in incident_types:
        TipoIncidencia.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "descripcion": desc,
                "requiere_evidencia": req_ev,
                "activo": True
            }
        )
    print("[OK] Incident types created.")
    
    print("=== SEEDING COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    seed()
