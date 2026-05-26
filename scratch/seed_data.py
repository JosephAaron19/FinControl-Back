import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Rol, Sede, Usuario

print("=== POBLANDO LA BASE DE DATOS CON DATOS DE SEMILLA ===")

# 1. Crear Roles
roles_data = [
    {'codigo': 'ADMIN', 'nombre': 'Administrador', 'descripcion': 'Acceso total al panel administrativo'},
    {'codigo': 'OPERADOR', 'nombre': 'Operador', 'descripcion': 'Usuario operativo normal'},
    {'codigo': 'ASESOR', 'nombre': 'Asesor', 'descripcion': 'Usuario operativo asesor con actividades de campo'}
]

roles = {}
for r_data in roles_data:
    rol, created = Rol.objects.get_or_create(codigo=r_data['codigo'], defaults=r_data)
    roles[r_data['codigo']] = rol
    if created:
        print(f"[+] Rol creado: {rol.nombre}")
    else:
        print(f"[*] Rol ya existe: {rol.nombre}")

# 2. Crear Sede Central
sede_data = {
    'nombre': 'Sede Central - Finhold',
    'direccion': 'Calle Las Orquídeas 456, San Isidro',
    'latitud': -12.04637400,
    'longitud': -77.04279300,
    'radio_metros': 100,
    'activo': True
}

sede, created = Sede.objects.get_or_create(nombre=sede_data['nombre'], defaults=sede_data)
if created:
    print(f"[+] Sede creada: {sede.nombre}")
else:
    print(f"[*] Sede ya existe: {sede.nombre}")

# 3. Crear Usuarios
usuarios_data = [
    {
        'dni': '12345678',
        'nombre_completo': 'Juan Pérez (Admin)',
        'cargo': 'Administrador de FinControl',
        'sede': sede,
        'rol': roles['ADMIN'],
        'is_staff': True,
        'is_superuser': True
    },
    {
        'dni': '12345679',
        'nombre_completo': 'Pedro Gómez (Operador)',
        'cargo': 'Operador Operativo',
        'sede': sede,
        'rol': roles['OPERADOR'],
        'is_staff': False,
        'is_superuser': False
    },
    {
        'dni': '12345680',
        'nombre_completo': 'Carlos Ruiz (Asesor)',
        'cargo': 'Asesor de Campo',
        'sede': sede,
        'rol': roles['ASESOR'],
        'is_staff': False,
        'is_superuser': False
    }
]

for u_data in usuarios_data:
    dni = u_data['dni']
    password = '123456'
    
    user = Usuario.objects.filter(dni=dni).first()
    if not user:
        user = Usuario.objects.create_user(
            dni=dni,
            password=password,
            nombre_completo=u_data['nombre_completo'],
            cargo=u_data['cargo'],
            sede=u_data['sede'],
            rol=u_data['rol'],
            is_staff=u_data['is_staff'],
            is_superuser=u_data['is_superuser']
        )
        print(f"[+] Usuario creado: {user.nombre_completo} (DNI: {dni}, Password: {password})")
    else:
        print(f"[*] Usuario ya existe: {user.nombre_completo} (DNI: {dni})")

print("=== PROCESO DE SEMILLA COMPLETADO CON ÉXITO ===")
