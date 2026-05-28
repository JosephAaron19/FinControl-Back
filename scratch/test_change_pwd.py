import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario, UsuarioSede
from api.views import get_authorized_sedes_ids

# Simular lo que hace change_password con el gerente Roberto
gerente = Usuario.objects.get(dni='40137397')
rol_nombre = gerente.rol.nombre.lower() if gerente.rol else ''
rol_codigo = (gerente.rol.codigo or '').lower() if gerente.rol else ''

print(f'Gerente: {gerente.nombre_completo}')
print(f'rol_nombre={repr(rol_nombre)}, rol_codigo={repr(rol_codigo)}')
print(f'Es gerente por nombre: {"gerente" in rol_nombre}')
print(f'Es gerente por codigo: {"gerente" in rol_codigo}')

sedes_ids = get_authorized_sedes_ids(gerente)
print(f'Sedes autorizadas del gerente: {sedes_ids}')

if sedes_ids:
    usuarios_sede = Usuario.objects.filter(sede_id__in=sedes_ids)
    print(f'Usuarios en sus sedes ({usuarios_sede.count()}):')
    for u in usuarios_sede:
        print(f'  - {u.nombre_completo} (DNI:{u.dni}) rol:{u.rol.nombre if u.rol else None} sede_id:{u.sede_id}')
else:
    print('Sin sedes asignadas - usuarios creados por el gerente:')
    usuarios_creados = Usuario.objects.filter(creado_por=gerente)
    for u in usuarios_creados:
        print(f'  - {u.nombre_completo} (DNI:{u.dni})')

# Test change_password: buscar un usuario de sus sedes
if sedes_ids:
    target = Usuario.objects.filter(sede_id__in=sedes_ids).first()
    if target:
        print(f'\nTest change_password: Gerente puede cambiar pw de {target.nombre_completo}? -> ', end='')
        found = Usuario.objects.filter(pk=target.pk, sede_id__in=sedes_ids).first()
        print('SI' if found else 'NO')
