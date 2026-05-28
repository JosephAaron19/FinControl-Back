import os
import sys
import django

# Add the parent directory to the path so django settings can be loaded
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Usuario, UsuarioHorario, HorarioDetalle, Horario
from datetime import date, datetime
import zoneinfo

lima_tz = zoneinfo.ZoneInfo('America/Lima')
today = datetime.now(lima_tz).date()
print('Fecha hoy (Lima):', today, '| Dia semana:', ['lunes','martes','miercoles','jueves','viernes','sabado','domingo'][today.weekday()])
print('-----------------------------------------')

print('USUARIOS:')
for u in Usuario.objects.all():
    print(f'User: {u.nombre_completo} (DNI: {u.dni}) | Sede: {u.sede.nombre if u.sede else "None"} | Activo: {u.is_active}')

print('\nUSUARIO HORARIOS:')
for uh in UsuarioHorario.objects.all().select_related('usuario','horario'):
    vigente = (uh.vigente_desde <= today) and (uh.vigente_hasta is None or uh.vigente_hasta >= today)
    print(f'User: {uh.usuario.nombre_completo} ({uh.usuario.dni}) | Horario: {uh.horario.nombre} (Activo: {uh.horario.activo}) | Activo UH: {uh.activo} | vigente_desde: {uh.vigente_desde} | vigente_hasta: {uh.vigente_hasta} | Vigente hoy: {vigente}')

print('\nHORARIO DETALLES:')
for hd in HorarioDetalle.objects.all().select_related('horario'):
    print(f'Horario: {hd.horario.nombre} | Dia: {hd.dia_semana} | Entrada: {hd.hora_inicio_entrada} - {hd.hora_fin_entrada} | Salida: {hd.hora_inicio_salida} - {hd.hora_fin_salida} | Activo: {hd.activo}')
