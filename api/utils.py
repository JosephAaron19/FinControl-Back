from datetime import datetime, date
from django.utils import timezone
from .models import Usuario, Sede, JornadaConfiguracion, Asistencia, HistorialJornada
from zoneinfo import ZoneInfo

def sync_daily_attendance(target_date=None):
    """
    Crea registros 'programada' para todos los usuarios que deberían trabajar hoy
    según la configuración de su sede.
    """
    if target_date is None:
        target_date = timezone.now().astimezone(ZoneInfo('America/Lima')).date()
    
    # Obtener día de la semana en español
    dias = {
        0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 
        4: 'viernes', 5: 'sabado', 6: 'domingo'
    }
    dia_nombre = dias[target_date.weekday()]
    
    # 1. Sedes con jornada configurada para hoy
    configs = JornadaConfiguracion.objects.filter(dia_semana=dia_nombre, activo=True)
    
    created_count = 0
    for config in configs:
        # 2. Usuarios de esa sede (Operadores y Asesores)
        usuarios = Usuario.objects.filter(
            sede=config.sede, 
            rol__nombre__iregex=r'(operador|asesor)',
            activo=True
        )
        
        for usuario in usuarios:
            # 3. Verificar si ya existe asistencia
            asistencia, created = Asistencia.objects.get_or_create(
                usuario=usuario,
                fecha=target_date,
                defaults={'estado_asistencia': 'programada'}
            )
            
            # Crear historial si no existe
            historial, h_created = HistorialJornada.objects.get_or_create(
                usuario=usuario,
                fecha=target_date,
                defaults={
                    'asistencia': asistencia,
                    'sede_id': config.sede_id,
                    'estado_asistencia': 'programada'
                }
            )
            
            if h_created and not created:
                historial.asistencia = asistencia
                historial.save()
            
            if h_created:
                created_count += 1
                
    return created_count

def close_expired_journeys():
    """
    Cierra jornadas de días PASADOS que quedaron abiertas o sin marcar.
    El cierre automático solo ocurre para registros cuya fecha es anterior a hoy.
    Esto permite que durante el día actual, el usuario pueda marcar tarde
    sin que el sistema le cierre la jornada automáticamente.
    """
    now_local = timezone.now().astimezone(ZoneInfo('America/Lima'))
    today = now_local.date()
    
    # 1. AUSENTES: Quedaron en 'programada' de días anteriores
    asistencias_pendientes = Asistencia.objects.filter(
        fecha__lt=today,
        estado_asistencia='programada'
    )
    
    for asis in asistencias_pendientes:
        asis.estado_asistencia = 'ausente'
        asis.estado = 'no_marco_entrada'
        asis.estado_puntualidad = 'no_marco_entrada'
        asis.estado_salida = 'no_marco_salida'
        asis.save()
        
        historial = HistorialJornada.objects.filter(asistencia=asis).first()
        if historial:
            historial.estado_asistencia = 'ausente'
            historial.estado_puntualidad = 'no_marco_entrada'
            historial.estado_salida = 'no_marco_salida'
            historial.estado_jornada = 'cerrada'
            historial.cerrado = True
            historial.cerrado_at = now_local
            historial.save()

    # 2. INCOMPLETAS: Quedaron en 'en_proceso' de días anteriores
    asistencias_incompletas = Asistencia.objects.filter(
        fecha__lt=today,
        estado_asistencia='en_proceso'
    )
    
    for asis in asistencias_incompletas:
        asis.estado_asistencia = 'incompleta'
        asis.estado_salida = 'no_marco_salida'
        asis.save()
        
        historial = HistorialJornada.objects.filter(asistencia=asis).first()
        if historial:
            historial.estado_asistencia = 'incompleta'
            historial.estado_salida = 'no_marco_salida'
            historial.estado_jornada = 'cerrada'
            historial.cerrado = True
            historial.cerrado_at = now_local
            historial.save()
